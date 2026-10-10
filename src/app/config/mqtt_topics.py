TOPICS = {
    "CAPTURE_REQUEST": "proto13/capture/request",
    "CAPTURE_RESULT": "proto13/capture/result",
    "SYSTEM_STATUS": "proto13/system/status",
    "DIAGNOSTICS": "proto13/system/diagnostics",
    "QUEUE_UPDATE": "proto13/queue/update",
}

MODE_CONFIG = {
    "SORT_ONLY": "sort_only",
    "INVENTORY_AND_SORT": "inventory_and_sort",
}

QUEUE_ACTIONS = {
    "ADVANCE_CARD": "advance_card",
    "TAKE_PICTURE": "take_picture",
    "TURN_TO_COLOR": "turn_to_color",
    "TURN_BY_DEGREES": "turn_by_degrees",
    "RETURN_HOME": "return_home",
    "RELEASE_CARD": "release_card",
}

EV3_QUEUE_MESSAGES = QUEUE_ACTIONS.copy()
