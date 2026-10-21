import json
import logging
from types import SimpleNamespace

from src.app.config.mqtt_settings import MqttConfig
from src.app.controller import Controller
from src.app.logging_setup import JsonFormatter
from src.app.services.mqtt_service import MqttService
from src.app.storage.event_store import EventStore


class FakeClient:
    def __init__(self):
        self.published = []
        self.subscribed = []
        self.will = None

    def will_set(self, topic, payload, qos=0, retain=False):
        self.will = (topic, json.loads(payload), retain)

    def connect(self, *args):
        pass

    def loop_start(self):
        self.on_connect(self, None, None, 0, None)

    def loop_stop(self):
        pass

    def disconnect(self):
        pass

    def subscribe(self, topic):
        self.subscribed.append(topic)

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, json.loads(payload), retain))
        return SimpleNamespace()


def make_controller():
    client = FakeClient()
    config = MqttConfig()
    service = MqttService(client=client, config=config)
    store = EventStore(":memory:")
    return Controller(service, store, config), client, store


def test_start_subscribes_sets_will_and_publishes_retained_status():
    controller, client, store = make_controller()
    controller.start()

    assert "proto13/controller/controller-01/#" in client.subscribed
    assert "proto13/+/+/status" in client.subscribed
    assert client.will[0] == "proto13/controller/controller-01/status"
    assert client.will[1]["online"] is False and client.will[2] is True
    topic, payload, retain = client.published[-1]
    assert topic == "proto13/controller/controller-01/status"
    assert payload["state"] == "ready" and retain is True
    assert store.recent()[0]["direction"] == "out"


def test_incoming_messages_are_stored_with_request_id():
    controller, client, store = make_controller()
    controller.start()
    controller.service._on_message(
        client,
        None,
        SimpleNamespace(
            topic="proto13/controller/controller-01/capture/result",
            payload=json.dumps(
                {"type": "capture_result", "request_id": "r1", "card_name": "Bolt"}
            ).encode(),
        ),
    )
    row = store.recent()[0]
    assert (row["direction"], row["type"], row["request_id"]) == (
        "in",
        "capture_result",
        "r1",
    )


def test_status_request_gets_correlated_reply():
    controller, client, _ = make_controller()
    controller.start()
    controller.handle_message(
        "proto13/controller/controller-01/status/request",
        {"type": "run_status_check", "request_id": "abc"},
    )
    assert client.published[-1][1]["request_id"] == "abc"


def test_own_status_echo_is_ignored():
    controller, client, store = make_controller()
    controller.start()
    before = len(store.recent())
    controller.handle_message(controller.own_status_topic, {"type": "system_status"})
    assert len(store.recent()) == before


def test_json_formatter_includes_extra_fields():
    record = logging.LogRecord("proto13.x", logging.INFO, "f", 1, "hello", None, None)
    record.request_id = "r1"
    entry = json.loads(JsonFormatter().format(record))
    assert entry["event"] == "hello" and entry["request_id"] == "r1"


def test_android_progress_results_keep_capture_in_flight():
    controller, client, _ = make_controller()
    controller.start()
    controller.handle_message(
        "proto13/controller/controller-01/request",
        {"type": "enqueue_capture", "request_id": "c1"},
    )
    queue = controller.android_queue
    assert queue.snapshot()["in_flight"] == "c1"
    for status in ("accepted", "in_progress"):
        controller.handle_message(
            "proto13/controller/controller-01/capture/result",
            {"type": "capture_result", "request_id": "c1", "status": status},
        )
        assert queue.snapshot()["in_flight"] == "c1"
        assert queue.snapshot()["faulted"] is False
    controller.handle_message(
        "proto13/controller/controller-01/capture/result",
        {"type": "capture_result", "request_id": "c1", "status": "success"},
    )
    assert queue.snapshot()["in_flight"] is None
