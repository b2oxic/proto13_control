ENTITY_TYPES = frozenset({"controller", "android", "ev3"})


def entity_topic(entity_type: str, device_id: str, channel: str) -> str:
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    if not device_id or any(character in device_id for character in "/+#"):
        raise ValueError("device_id must be a non-empty MQTT topic segment")
    if not channel or any(part in {"", "+", "#"} for part in channel.split("/")):
        raise ValueError("channel must contain valid MQTT topic segments")
    return f"proto13/{entity_type}/{device_id}/{channel}"


def status_request_topic(entity_type: str, device_id: str) -> str:
    return entity_topic(entity_type, device_id, "status/request")


def status_topic(entity_type: str, device_id: str) -> str:
    return entity_topic(entity_type, device_id, "status")


def component_request_topic(entity_type: str, device_id: str) -> str:
    return entity_topic(entity_type, device_id, "request")


def controller_capture_result_topic(device_id: str) -> str:
    return entity_topic("controller", device_id, "capture/result")


MODE_CONFIG = {
    "SORT_ONLY": "sort_only",
    "INVENTORY_AND_SORT": "inventory_and_sort",
}

QUEUE_ACTIONS = {
    "ADVANCE_CARD": "advance_card",
    "TURN_TO_COLOR": "turn_to_color",
    "TURN_BY_DEGREES": "turn_by_degrees",
    "RETURN_HOME": "return_home",
    "RELEASE_CARD": "release_card",
}

EV3_QUEUE_MESSAGES = QUEUE_ACTIONS.copy()
