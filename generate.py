#!/usr/bin/env python3

import argparse
import base64
import json
import os
import requests
from pathlib import PurePath


def calculate_checksum(command: str = b''):
    checksum = 0
    for i in range(0, len(command)):
        checksum ^= command[i]
    return checksum.to_bytes()


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
    with open(load_file, 'r') as f:
        data = json.load(f)
else:
    # Request the available scenes from the publicly available API
    print(f"Requesting scenes data for SKU '{args.sku}'...")
    headers = { "AppVersion": f"{args.appversion}","User-Agent": f"GoveeHome/{args.appversion} (com.ihoment.GoVeeSensor; build:2; iOS 16.5.0) Alamofire/5.6.4"}
    response = requests.get(f"https://app2.govee.com/appsku/v1/light-effect-libraries?sku={args.sku}", headers=headers)
    data = json.loads(response.text)

    if args.cache:
        save_file = base_directory / f"govee_{args.sku}_api_data.json"
        with open(save_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved the API response data as {save_file}.")


# Extract only scenes from received data
scenes = [scene for category in data['data']['categories'] for scene in category['scenes']]
print(f"Extracted {len(scenes)} scenes.")
del(data)

new_scenes = {}

# Process data
for scene in scenes:
    scene_code = scene["lightEffects"][0]["sceneCode"]
    
    # Convert base64 effect value ("scenceParam") to hex values
    hex_command = base64.b64decode(scene["lightEffects"][0]["scenceParam"].encode('ascii'))

    # hex_command actually consist of multiple subcommands that are sent to the controller.
    # Count individual commands (or "lines") and convert those values to hex.
    num_bytes = len(hex_command) + 3 + 13
    # Bytes that do not fit (division remainder) seem to be discarded.
    num_commands = num_bytes // 17

    # Add general prefixes and suffixes to the whole command
    hex_command = b'\x01' + num_commands.to_bytes() + b'\x02' + hex_command + b'\x00' * 13

    # Add subcommand counter prefixes as well as the special last subcommand prefix
    subcommands = []
    for i in range(num_commands):
        if i != num_commands - 1:
            subcommand_prefix = i.to_bytes()
        else:
            subcommand_prefix = b'\xff'

        # Ignore the newly added prefix and read exactly 17 bytes every time
        start_index = i * 17
        
        # Cut the hex_command to num_commands of smaller subcommands and prepend the multiline prefix to them
        subcommand = b'\xa3' + subcommand_prefix + hex_command[start_index:start_index+17]
        subcommand += calculate_checksum(subcommand)
        subcommands.append(base64.b64encode(subcommand).decode('ascii'))

    # Also send a scene code subcommand. We need to flip the byte order here. The prefix here is special, as well as a padding instead of the suffix.
    scene_code_subcommand = b'\x33\x05\x04' + scene_code.to_bytes(2, byteorder='little') + b'\x00' * 14
    scene_code_subcommand += calculate_checksum(scene_code_subcommand)
    subcommands.append(base64.b64encode(scene_code_subcommand).decode('ascii'))

    # Assemble the final pretty dictionary
    new_scenes[scene["sceneName"]] = {
        'scene_code': scene_code,
        'command': subcommands,
    }

del(scenes)

save_file = base_directory / f"govee_{args.sku}_scenes.json"
with open(save_file, 'w') as f:
    json.dump(new_scenes, f, indent=4)
print(f"Saved the final JSON data to {save_file}.")
