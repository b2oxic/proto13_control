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
