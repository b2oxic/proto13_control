from src.app.config.mqtt_topics import MODE_CONFIG, QUEUE_ACTIONS, TOPICS
from src.app.topics.topic_contracts import QUEUE_UPDATE


def test_topics_are_defined():
    assert TOPICS["CAPTURE_REQUEST"] == "proto13/capture/request"
    assert TOPICS["CAPTURE_RESULT"] == "proto13/capture/result"
    assert TOPICS["SYSTEM_STATUS"] == "proto13/system/status"
    assert TOPICS["QUEUE_UPDATE"] == "proto13/queue/update"


def test_modes_are_defined():
    assert MODE_CONFIG["SORT_ONLY"] == "sort_only"
    assert MODE_CONFIG["INVENTORY_AND_SORT"] == "inventory_and_sort"


def test_ev3_queue_actions_are_defined():
    assert QUEUE_ACTIONS["ADVANCE_CARD"] == "advance_card"
    assert QUEUE_ACTIONS["TURN_TO_COLOR"] == "turn_to_color"
    assert QUEUE_ACTIONS["TURN_BY_DEGREES"] == "turn_by_degrees"
    assert QUEUE_ACTIONS["RETURN_HOME"] == "return_home"
    assert QUEUE_ACTIONS["RELEASE_CARD"] == "release_card"
    assert QUEUE_ACTIONS["TAKE_PICTURE"] == "take_picture"

    assert "action" in QUEUE_UPDATE
    assert "target_color" in QUEUE_UPDATE
    assert "degrees" in QUEUE_UPDATE
    assert "return_home" in QUEUE_UPDATE["action"]
    assert "release_card" in QUEUE_UPDATE["action"]
    assert "take_picture" in QUEUE_UPDATE["action"]
