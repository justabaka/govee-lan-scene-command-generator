# Govee LAN Scene Command Generator
> [!WARNING]
> LAN Scene control is an undocumented protocol, it may change or break at any time.

Calls the Govee API, retrieves the available scenes and converts them into usable LAN commands so you are no longer vendor locked and actually may switch your Govee scenes using third party software.

## Installation
Clone the repository (or download the script + txt files manually) and install project requirements:
* `git clone https://github.com/justabaka/govee-lan-scene-command-generator.git`
* `pip install -r requirements.txt`

## IoT API and DIY Scenes
As far as the community found out, command structure may vary from model to model, so it may not work out of the box.
The easiest way to check if the commands you've generated are valid for your device is calling the IoT API which basically dumps ready commands for you. It's also a great way of obtaining commands for your DIY scenes.

Get token returned by this request:
```bash
curl --location 'https://community-api.govee.com/os/v1/login' --header 'Content-Type: application/json' --data '{"email": "email", "password": "password"}'
```
Returns the following JSON: `{"message":"Login successful","status":200,"data":{"token":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}`

Replace __token__ with an actual token (not including quotation marks):
```bash
curl --location 'https://app2.govee.com/bff-app/v1/exec-plat/home' --header 'Content-Type: application/json' --header 'appVersion: 6.6.30' --header 'Authorization: Bearer __token__'
```

## Example
You may use any Govee LAN API command as a template, just make sure you set `"cmd": "ptReal"`.
```python
import json
import socket

LOCAL_IP_ADDRESS = '192.168.0.100'
CONTROLLER_IP_ADDRESS = '192.168.0.10'
LISTEN_PORT = 4002
COMMAND_PORT = 4003

command = { "msg": { "cmd": "ptReal", "data": { "command": ["owABCQIEGgAAAAECAeVqAcgUCu0=", "owEA/TIB////AwCAAAAAACMAAjE=", "owIHAwAB/wUAoBQUAeYKBP///+g=", "owOFzv6m//8I/vARAcgSAeABI7w=", "owQAAgcEAAH/AAPMFBQB5goE/4E=", "owX//1/X/6b//y3+4AEByAIB4G8=", "owYBHQACBQMAAf8AA9gUFAHmCnU=", "owcCZdX/Lf7gAQHIAgHgAgAAAPM=", "o/8AAAAAAAAAAAAAAAAAAAAAAFw=", "MwUEDi8AAAAAAAAAAAAAAAAAABM="] } } }

socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket.bind((LOCAL_IP_ADDRESS, LISTEN_PORT))

socket.sendto(bytes(json.dumps(command), "utf-8"), (CONTROLLER_IP_ADDRESS, COMMAND_PORT))
socket.close()
```

## References
* https://github.com/egold555/Govee-Reverse-Engineering/issues/11
* https://github.com/AlgoClaw/Govee/blob/main/decoded/explanation
* https://github.com/AlgoClaw/Govee/blob/main/decoded/govee_decoded.sh
* https://disbar.red/note/Govee%20Decoded%202