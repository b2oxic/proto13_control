CAPTURE_REQUEST = {
    "type": "capture_request",
    "request_id": "string",
    "device_id": "string",
    "mode": "sort_only | inventory_and_sort",
    "requested_at": "timestamp",
}

CAPTURE_RESULT = {
    "type": "capture_result",
    "request_id": "string",
    "device_id": "string",
    "card_name": "string",
    "match_confidence": "float",
    "mode": "sort_only | inventory_and_sort",
    "status": "accepted | in_progress | success | retry | failure",
    "error": "string | null",
    "processed_at": "timestamp",
}

STATUS_REQUEST = {
    "type": "run_status_check | run_diagnostics",
    "request_id": "string",
    "device_id": "string",
    "requested_at": "timestamp",
}

SYSTEM_STATUS = {
    "type": "system_status",
    "request_id": "string",
    "device_id": "string",
    "online": "bool",
    "state": "starting | ready | busy | degraded | fault",
    "mode": "sort_only | inventory_and_sort",
    "timestamp": "timestamp",
}

DIAGNOSTICS_RESULT = {
    "type": "diagnostics_result",
    "request_id": "string",
    "device_id": "string",
    "status": "success | warning | failure",
    "checks": "list",
    "timestamp": "timestamp",
}

EV3_QUEUE_COMMAND = {
    "type": "ev3_queue_command",
    "request_id": "string",
    "device_id": "string",
    "sequence": "int",
    "action": "advance_card | turn_to_color | turn_by_degrees | return_home | release_card",
    "target_color": "W | U | B | R | G | M | null",
    "degrees": "int | null",
    "card_id": "string | null",
    "timestamp": "timestamp",
}

EV3_COMMAND_RESULT = {
    "type": "ev3_command_result",
    "request_id": "string",
    "device_id": "string",
    "status": "accepted | in_progress | complete | failed",
    "error": "string | null",
    "timestamp": "timestamp",
}
