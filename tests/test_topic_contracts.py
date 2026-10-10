from src.app.config.mqtt_topics import MODE_CONFIG, TOPICS


def test_topics_are_defined():
    assert TOPICS["CAPTURE_REQUEST"] == "proto13/capture/request"
    assert TOPICS["CAPTURE_RESULT"] == "proto13/capture/result"
    assert TOPICS["SYSTEM_STATUS"] == "proto13/system/status"


def test_modes_are_defined():
    assert MODE_CONFIG["SORT_ONLY"] == "sort_only"
    assert MODE_CONFIG["INVENTORY_AND_SORT"] == "inventory_and_sort"
