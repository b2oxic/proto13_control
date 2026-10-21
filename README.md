# Proto13 Controller

This project is the controller application for the Proto13 card sorting pipeline. It uses a separate MQTT broker (Mosquitto) to communicate with Android and EV3 components.

## Purpose

The controller is responsible for coordinating the flow between:
- the Android card-recognition app
- the EV3 sorting logic
- inventory/status tracking
- queue and diagnostics monitoring

## Responsibilities

- Handle capture trigger messages
- Publish card recognition result messages
- Expose health and status topics
- Manage queue state and routing requests
- Provide a clean integration layer for the Android scanner and downstream systems

## Target deployment

- Current: Windows-based execution
- Future: Linux containerized deployment

## Proposed topic layout

- `proto13/android/{android_id}/request` - controller asks that Android imager to capture and recognize a card (`type: capture_request`, includes `request_id`)
- `proto13/controller/{controller_id}/capture/result` - Android imager publishes the correlated result; that controller subscribes
- `proto13/ev3/{ev3_id}/request` - controller asks that EV3 to sort (`type: ev3_queue_command`)
- `proto13/{entity_type}/{device_id}/status/request` - send `run_status_check` or `run_diagnostics`, with a `request_id`
- `proto13/{entity_type}/{device_id}/status` - status, diagnostics, or EV3 command result, correlated by `request_id`

## Planned modes

- sort-only
- inventory-and-sort

## How to run

Clone the repository and install the dependency set:

```powershell
cd proto13_control
python -m pip install -r requirements.txt
```

Run the bootstrap launcher, which checks for `paho-mqtt`, installs it if
missing, and then launches the app entry point:

```powershell
python run_mqtt.py
```

You can also launch the module entry point directly:

```powershell
python -m src.app
```

The app can publish EV3 queue commands using the configured broker. Set these
environment variables before launching it:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MQTT_BROKER_HOST` | `198.168.0.40` | MQTT broker hostname or IP address |
| `MQTT_BROKER_PORT` | `1883` | MQTT broker port |
| `MQTT_CLIENT_ID` | `proto13_control` | Unique ID for this publisher connection |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | unset | Optional broker credentials |
| `MQTT_EV3_DEVICE_ID` | `ev3-01` | Default EV3 target ID; each EV3 subscribes to its own request topic |
| `MQTT_KEEPALIVE` | `60` | MQTT keepalive interval in seconds |

For example, send a color-turn command with:

```powershell
$env:MQTT_BROKER_HOST = "198.168.0.40"
python run_mqtt.py send-ev3-command turn_to_color --device-id ev3-01 --target-color R
```

Each EV3 must connect to the same broker and subscribe to its own request topic,
such as `proto13/ev3/ev3-01/request`. MQTT delivers by topic, not by
device ID in the payload. The request is JSON, has a unique `request_id`, and
follows the `EV3_QUEUE_COMMAND` contract. EV3 completion/failure belongs in an
`EV3_COMMAND_RESULT` response on its status topic, not in the command request.
The service and its publisher behavior can be unit-tested with a fake MQTT
client without a broker.

## Legacy MQTT protocol notes

The earlier prototype used a controller topic that could be overridden with
`--topic`, defaulting to `mtgproto14/controller`, while image storage could be
changed with `--base`. The reference database was always loaded from the project
local reference JSON, independent of the active working directory or storage
location.

The service subscribed on connection and reconnection. Only the exact payload
`imager_analyze_card` triggered a capture. Responses on the same topic were of
the form `sorter_move_to_<code>`, where the code was W, U, B, R, G, or M for
multicolor cards. The original protocol used an empty suffix for both colorless
cards and unidentified or failed captures; these could not be distinguished by
the sorter. Destination mappings should be confirmed on the EV3 before operating
the mechanism.

