import json
from uuid import UUID

from src.app.config.mqtt_settings import MqttConfig
from src.app.config.mqtt_topics import (
    MODE_CONFIG,
    QUEUE_ACTIONS,
    component_request_topic,
    status_request_topic,
    status_topic,
)
from src.app.services.mqtt_service import MqttService
from src.app.__main__ import _build_ev3_queue_command
from src.app.topics.topic_contracts import (
    CAPTURE_REQUEST,
    CAPTURE_RESULT,
    DIAGNOSTICS_RESULT,
    EV3_COMMAND_RESULT,
    EV3_QUEUE_COMMAND,
    STATUS_REQUEST,
    SYSTEM_STATUS,
)


def test_topics_are_defined():
    assert component_request_topic("ev3", "ev3-01") == (
        "proto13/ev3/ev3-01/request"
    )
    assert component_request_topic("android", "android-01") == (
        "proto13/android/android-01/request"
    )
    assert status_request_topic("android", "android-01") == (
        "proto13/android/android-01/status/request"
    )
    assert status_topic("android", "android-01") == "proto13/android/android-01/status"
    assert component_request_topic("ev3", "ev3-02") != component_request_topic(
        "ev3", "ev3-01"
    )


def test_modes_are_defined():
    assert MODE_CONFIG["SORT_ONLY"] == "sort_only"
    assert MODE_CONFIG["INVENTORY_AND_SORT"] == "inventory_and_sort"


def test_ev3_queue_actions_are_defined():
    assert QUEUE_ACTIONS["ADVANCE_CARD"] == "advance_card"
    assert QUEUE_ACTIONS["TURN_TO_COLOR"] == "turn_to_color"
    assert QUEUE_ACTIONS["TURN_BY_DEGREES"] == "turn_by_degrees"
    assert QUEUE_ACTIONS["RETURN_HOME"] == "return_home"
    assert QUEUE_ACTIONS["RELEASE_CARD"] == "release_card"

    assert "action" in EV3_QUEUE_COMMAND
    assert "device_id" in EV3_QUEUE_COMMAND
    assert "request_id" in EV3_QUEUE_COMMAND
    assert "target_color" in EV3_QUEUE_COMMAND
    assert "degrees" in EV3_QUEUE_COMMAND
    assert "return_home" in EV3_QUEUE_COMMAND["action"]
    assert "release_card" in EV3_QUEUE_COMMAND["action"]
    assert "take_picture" not in EV3_QUEUE_COMMAND["action"]
    assert "status" not in EV3_QUEUE_COMMAND


def test_requests_and_responses_support_correlation():
    assert "request_id" in CAPTURE_REQUEST
    assert "request_id" in CAPTURE_RESULT
    assert "request_id" in STATUS_REQUEST
    assert "request_id" in SYSTEM_STATUS
    assert "request_id" in DIAGNOSTICS_RESULT
    assert "request_id" in EV3_COMMAND_RESULT


def test_ev3_command_has_unique_request_id_and_no_outcome_status():
    payload = _build_ev3_queue_command(
        device_id="ev3-01",
        action="return_home",
        sequence=1,
        target_color=None,
        degrees=None,
        card_id=None,
    )

    UUID(str(payload["request_id"]))
    assert payload["device_id"] == "ev3-01"
    assert payload["type"] == "ev3_queue_command"
    assert "status" not in payload


def test_mqtt_config_reads_broker_settings_from_environment(monkeypatch):
    monkeypatch.setenv("MQTT_BROKER_HOST", "broker.local")
    monkeypatch.setenv("MQTT_BROKER_PORT", "1884")
    monkeypatch.setenv("MQTT_CLIENT_ID", "proto13_sender")
    monkeypatch.setenv("MQTT_EV3_DEVICE_ID", "ev3-02")

    config = MqttConfig.from_environment()

    assert config.broker_host == "broker.local"
    assert config.broker_port == 1884
    assert config.client_id == "proto13_sender"
    assert config.ev3_device_id == "ev3-02"
    assert config.ev3_request_topic == "proto13/ev3/ev3-02/request"


def test_mqtt_service_publishes_json_to_client():
    class FakeClient:
        def publish(self, topic, payload, qos, retain=False):
            self.message = (topic, payload, qos)

    client = FakeClient()
    service = MqttService(client=client)
    payload = {"action": "return_home", "sequence": 1}

    service.publish(component_request_topic("ev3", "ev3-01"), payload)

    assert client.message == (
        "proto13/ev3/ev3-01/request",
        json.dumps(payload),
        1,
    )


def test_mqtt_service_waits_for_connection_callback():
    class FakeClient:
        def connect(self, host, port, keepalive):
            self.connection = (host, port, keepalive)

        def loop_start(self):
            self.on_connect(self, None, None, 0, None)

        def loop_stop(self):
            pass

        def disconnect(self):
            pass

    client = FakeClient()
    service = MqttService(client=client)

    service.connect()

    assert client.connection == ("192.168.0.55", 1883, 60)
    assert service._connected_event.is_set()
    service.disconnect()
