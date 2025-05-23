# Govee LAN Scene Command Generator
> [!WARNING]
> LAN Scene control is an undocumented protocol, it may change or break at any time.

Calls the Govee API, retrieves the available scenes and converts them into usable LAN commands so you are no longer vendor locked and actually may switch your Govee scenes using third party software.

## Installation
Clone the repository (or download the script + txt files manually) and install project requirements:
* `git clone https://github.com/justabaka/govee-lan-scene-command-generator.git`
* `pip install -r requirements.txt` - it is better to use [virtual environments](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#create-and-use-virtual-environments) or tools like [uv](https://github.com/astral-sh/uv), [Poetry](https://github.com/python-poetry/poetry), [Pipenv](https://github.com/pypa/pipenv) or [pipx](https://github.com/pypa/pipx).

## Usage
```shell
Usage: ./generate.py [-h] -s SKU [-a APPVERSION] [-l FILENAME] [-c]

Options:
  -h, --help                   Show this help message and exit
  -s, --sku SKU                Your Govee Device SKU (Model). For example, H61F2
  -a, --appversion APPVERSION  The desired GoveeHome app version. Default value is 9999999
  -l, --load FILENAME          Path to a file to load the API response data (JSON) from instead of requesting it via Govee API
  -c, --cache                  Cache the API response data (JSON) to a file
  ```

## IoT API and DIY Scenes
As far as the community found out, command structure may vary from model to model, so it may not work out of the box.
The easiest way to check if the commands you've generated are valid for your device is calling the IoT API which basically dumps ready to use scene commands.
It is also a great way of obtaining commands for your DIY scenes. All you need to do is create a Tap-to-run action that runs your regular/DIY scene in the Govee Home app, and it will appear in the IoT API response.

Get token returned by this request:
```bash
curl --location 'https://community-api.govee.com/os/v1/login' --header 'Content-Type: application/json' --data '{"email": "email", "password": "password"}'
```
Returns the following JSON: `{"message":"Login successful","status":200,"data":{"token":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}`

Replace `__token__` with an actual token (not including quotation marks):
```bash
curl --location 'https://app2.govee.com/bff-app/v1/exec-plat/home' --header 'Content-Type: application/json' --header 'appVersion: 6.6.30' --header 'Authorization: Bearer __token__'
```

## Example
You may use any Govee LAN API command as a template, just make sure you set `"cmd": "ptReal"`.
```python
#!/usr/bin/env python3

import json
import socket

LOCAL_IP_ADDRESS = '192.168.0.100'
CONTROLLER_IP_ADDRESS = '192.168.0.10'
LISTEN_PORT = 4002
COMMAND_PORT = 4003

command = { "msg": { "cmd": "ptReal", "data": { "command": ["owABCQIEGgAAAAECAeVqAcgUCu0=", "owEA/TIB////AwCAAAAAACMAAjE=", "owIHAwAB/wUAoBQUAeYKBP///+g=", "owOFzv6m//8I/vARAcgSAeABI7w=", "owQAAgcEAAH/AAPMFBQB5goE/4E=", "owX//1/X/6b//y3+4AEByAIB4G8=", "owYBHQACBQMAAf8AA9gUFAHmCnU=", "owcCZdX/Lf7gAQHIAgHgAgAAAPM=", "o/8AAAAAAAAAAAAAAAAAAAAAAFw=", "MwUEDi8AAAAAAAAAAAAAAAAAABM="] } } }

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((LOCAL_IP_ADDRESS, LISTEN_PORT))

s.sendto(bytes(json.dumps(command), "utf-8"), (CONTROLLER_IP_ADDRESS, COMMAND_PORT))
s.close()
```

## References
* https://blog.coding.kiwi/reverse-engineering-govee-smart-lights/
* https://github.com/AlgoClaw/Govee/blob/main/decoded/v1.2/explanation_v1.2.md
* https://github.com/egold555/Govee-Reverse-Engineering/issues/11
* https://disbar.red/note/Govee%20Decoded%202
