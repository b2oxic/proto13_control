CAPTURE_REQUEST = {
    "type": "capture_request",
    "device_id": "string",
    "mode": "sort_only | inventory_and_sort",
    "requested_at": "timestamp",
}

CAPTURE_RESULT = {
    "type": "capture_result",
    "device_id": "string",
    "card_name": "string",
    "match_confidence": "float",
    "mode": "sort_only | inventory_and_sort",
    "status": "success | retry | failure",
    "processed_at": "timestamp",
}

SYSTEM_STATUS = {
    "type": "system_status",
    "device_id": "string",
    "online": "bool",
    "mode": "sort_only | inventory_and_sort",
    "timestamp": "timestamp",
}

QUEUE_UPDATE = {
    "type": "queue_update",
    "sequence": "int",
    "action": "advance_card | take_picture | turn_to_color | turn_by_degrees | return_home | release_card",
    "target_color": "W | U | B | R | G | M | null",
    "degrees": "int | null",
    "card_id": "string | null",
    "status": "queued | in_progress | complete | failed",
    "timestamp": "timestamp",
}
