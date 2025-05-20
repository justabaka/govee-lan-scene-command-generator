#!/usr/bin/env python3
# pylint: disable=missing-module-docstring,line-too-long,invalid-name

import argparse
import base64
import itertools
import json
import math
import os
from pathlib import PurePath
import re
import requests


def calculate_checksum(command: str = b'') -> bytes:
    """ Calculate a contunuous XOR checksum of an input byte sequence (string)

    Args:
        command (str, optional): byte sequence of hex numbers. Defaults to b''.

    Returns:
        bytes: resulting checksum as a byte sequence.
    """
    checksum = 0
    for byte in command:
        checksum ^= byte
    return checksum.to_bytes()

CONTROL_CHARS = ''.join(map(chr, itertools.chain(range(0x00,0x20), range(0x7f,0xa1))))
control_chars_re = re.compile('[%s]' % re.escape(CONTROL_CHARS))

arg_parser = argparse.ArgumentParser(
    prog='Govee LAN Scene Command Generator',
    description='Gets a full list of Govee Scenes that are available for your Govee device via Govee API and converts that into pure LAN command list to call without depending on the Internet of Shit™',
)

arg_parser.add_argument('-s', '--sku', required=True, help="Your Govee Device SKU (Model). For example, H61F2.")
arg_parser.add_argument('-a', '--appversion', required=False, default="9999999", help="The desired GoveeHome app version. Default value is 9999999.")
arg_parser.add_argument('-l', '--load', required=False, default=None, help="Path to a file to load the API response data (JSON) from instead of requesting it via Govee API.")
arg_parser.add_argument('-c', '--cache', required=False, default=False, action='store_true', help="Cache the API response data (JSON) to a file. Does not do anything if --load was used.")
args = arg_parser.parse_args()

base_directory = PurePath(__file__).parent
if not os.path.exists(base_directory):
    os.makedirs(base_directory)

if args.load is not None:
    # Load JSON from a file
    load_file = base_directory / args.load
    print(f"Loading data for SKU '{args.sku}' from file '{load_file}'...")
    with open(load_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
else:
    # Request the available scenes from the publicly available API
    print(f"Requesting scenes data for SKU '{args.sku}'...")
    headers = { "AppVersion": f"{args.appversion}","User-Agent": f"GoveeHome/{args.appversion} (com.ihoment.GoVeeSensor; build:2; iOS 16.5.0) Alamofire/5.6.4"}
    response = requests.get(f"https://app2.govee.com/appsku/v1/light-effect-libraries?sku={args.sku}", headers=headers, timeout=5)
    data = json.loads(response.text)

    if args.cache:
        save_file = base_directory / f"govee_{args.sku}_api_data.json"
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Saved the API response data as {save_file}.")

load_sku_data = base_directory / 'model_specific_parameters.json'
print(f"Loading SKU-specific data from file '{load_sku_data}'...")
with open(load_sku_data, 'r', encoding='utf-8') as f:
    sku_data = json.load(f)

sku_rules = {}
multiline_command_prefix = b'\xa3'

# Determine which SKU ruleset to use
for sku_group in sku_data:
    if args.sku in sku_group['models']:
        print(f"Found SKU-specific data for SKU '{args.sku}'.")
        sku_rules = sku_group
        if sku_rules["hex_multi_prefix"]:
            multiline_command_prefix = bytes.fromhex(sku_rules["hex_multi_prefix"])
            
        break

# Extract only scenes from received data
scenes = [scene for category in data['data']['categories'] for scene in category['scenes']]
extracted_scene_count = len(scenes)
print(f"Extracted {extracted_scene_count} scenes.")
del data

new_scenes = {}

# Process data
for scene in scenes:
    scene_code = scene["lightEffects"][0]["sceneCode"]

    # Convert base64 effect value ("scenceParam") to hex
    hex_command = base64.b64decode(scene["lightEffects"][0]["scenceParam"])
    mode_command_suffix = b''

    # Determine if the original scene command requires extra modification (e.g., adding/replacing/removing prefixes and suffixes)
    if "type" in sku_rules.keys():
        for scene_type in sku_rules["type"]:
            prefix_to_remove = bytes.fromhex(scene_type["hex_prefix_remove"])
            if hex_command.startswith(prefix_to_remove):
                hex_command = hex_command[len(prefix_to_remove):]

                if scene_type["hex_prefix_add"]:
                    hex_command = bytes.fromhex(scene_type["hex_prefix_add"]) + hex_command

                mode_command_suffix = bytes.fromhex(scene_type["normal_command_suffix"])

                break

    # hex_command actually consist of multiple subcommands that are sent to the controller.
    # We have to count individual subcommands (or "lines") before adding prefixes and suffixes since we need to include num_commands in the first subcommand.
    num_bytes = len(hex_command) + 3 # Add length of future prefixes (3) and padding/suffixes (13) (see below)
    num_commands = math.ceil(num_bytes / 17)

    # Add general prefixes and padding/suffixes to the whole command
    hex_command = b'\x01' + num_commands.to_bytes() + scene["lightEffects"][0]["sceneType"].to_bytes() + hex_command

    # Add subcommand counter prefixes as well as the special last subcommand prefix
    subcommands = []

    if sku_rules['on_command']:
        on_command = b'\x33\x01\x01' + b'\x00' * 16
        on_command += calculate_checksum(on_command)
        subcommands.append(base64.b64encode(on_command).decode('ascii'))

    for i in range(num_commands):
        if i != num_commands - 1:
            subcommand_prefix = i.to_bytes()
        else:
            subcommand_prefix = b'\xff'

        # Ignore the newly added prefix and read exactly 17 bytes every time
        start_index = i * 17

        # Cut the hex_command to num_commands of smaller subcommands and prepend the multiline prefix to them
        subcommand = multiline_command_prefix + subcommand_prefix + hex_command[start_index:start_index+17]

        # Also null-pad the command from the right if it's too short: it should be 19 bytes long at this point
        if len(subcommand) < 19:
            subcommand += b'\x00' * (19 - len(subcommand))

        subcommand += calculate_checksum(subcommand)
        subcommands.append(base64.b64encode(subcommand).decode('ascii'))

    # Also send a scene code subcommand. We need to flip the byte order here. The prefix here is special.
    scene_code_subcommand = b'\x33\x05\x04' + scene_code.to_bytes(2, byteorder='little') + mode_command_suffix
    scene_code_subcommand += b'\x00' * (19 - len(scene_code_subcommand))
    scene_code_subcommand += calculate_checksum(scene_code_subcommand)
    subcommands.append(base64.b64encode(scene_code_subcommand).decode('ascii'))

    # Strip Unicode control characters just in case
    scene_name = control_chars_re.sub('', scene["sceneName"])

    # Assemble the final dictionary
    new_scenes[scene_name] = {
        'scene_code': scene_code,
        'command': subcommands,
    }

# Check for anomalies
converted_scene_count = len(new_scenes)
print(f"Converted {converted_scene_count}/{extracted_scene_count} scenes.")
if converted_scene_count != extracted_scene_count:
    print("\nWARNING: Number of converted scenes does not match the number of extracted scenes!")
    scene_names = sorted([scene["sceneName"] for scene in scenes])
    dupes = [x for n, x in enumerate(scene_names) if x in scene_names[:n]]
    if dupes:
        print(f"WARNING: Found duplicate scenes {dupes}. Seems like Govee API sends its regards.\n")
    else:
        print("WARNING: Cannot find a valid reason for this. Please inspect the JSONs and file a bug report at https://github.com/justabaka/govee-lan-scene-command-generator/issues/new\n")

del scenes

save_file = base_directory / f"govee_{args.sku}_scenes.json"
with open(save_file, 'w', encoding='utf-8') as f:
    json.dump(new_scenes, f, indent=4)
print(f"Saved the final JSON data to {save_file}.")
