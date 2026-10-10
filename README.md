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
