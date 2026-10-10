# Proto13 MQTT Service

This project hosts the message-broker layer for the Proto13 card sort pipeline.

## Purpose

The MQTT service is responsible for coordinating the flow between:
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

- proto13/capture/request
- proto13/capture/result
- proto13/system/status
- proto13/system/diagnostics
- proto13/queue/update

## Planned modes

- sort-only
- inventory-and-sort

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
