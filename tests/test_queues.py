import json
from types import SimpleNamespace

from src.app.config.mqtt_settings import MqttConfig
from src.app.controller import Controller
from src.app.queues import DeviceQueue
from src.app.services.mqtt_service import MqttService
from src.app.storage.event_store import EventStore
from tests.test_controller import FakeClient


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_queue(name="ev3", **kwargs):
    sent = []
    clock = Clock()
    queue = DeviceQueue(
        name, f"{name}-01", f"proto13/{name}/{name}-01/request",
        lambda topic, payload: sent.append((topic, dict(payload))),
        timeout=10, max_retries=1, clock=clock, **kwargs,
    )
    return queue, sent, clock


def test_one_in_flight_and_advances_on_complete():
    queue, sent, _ = make_queue()
    first = queue.enqueue({"type": "ev3_queue_command", "action": "advance_card"})
    queue.enqueue({"type": "ev3_queue_command", "action": "release_card"})
    assert len(sent) == 1 and sent[0][1]["sequence"] == 1
    queue.complete(first)
    assert len(sent) == 2 and sent[1][1]["sequence"] == 2
    assert queue.depth == 1


def test_timeout_retries_then_faults_and_pauses():
    queue, sent, clock = make_queue()
    queue.enqueue({"action": "advance_card"})
    queue.enqueue({"action": "release_card"})
    clock.now = 11
    queue.tick()
    assert len(sent) == 2 and sent[1][1]["request_id"] == sent[0][1]["request_id"]
    clock.now = 22
    queue.tick()
    assert queue.faulted and queue.paused and queue.failed == 1
    assert len(sent) == 2  # second command is held, not sent
    queue.resume()
    assert len(sent) == 3 and not queue.faulted


def test_progress_extends_deadline():
    queue, sent, clock = make_queue()
    request_id = queue.enqueue({"action": "advance_card"})
    clock.now = 8
    queue.progress(request_id)
    clock.now = 15
    queue.tick()
    assert len(sent) == 1


def test_pause_holds_new_commands():
    queue, sent, _ = make_queue()
    queue.pause()
    queue.enqueue({"action": "advance_card"})
    assert sent == []
    queue.resume()
    assert len(sent) == 1


def test_stale_result_is_ignored():
    queue, sent, _ = make_queue()
    queue.enqueue({"action": "advance_card"})
    queue.complete("not-the-request")
    assert queue.depth == 1


def make_controller():
    client = FakeClient()
    config = MqttConfig()
    controller = Controller(MqttService(client=client, config=config), EventStore(":memory:"), config)
    controller.start()
    client.published.clear()
    return controller, client


def test_enqueue_commands_via_mqtt_publish_to_devices():
    controller, client = make_controller()
    controller.handle_message(
        "proto13/controller/controller-01/request",
        {"type": "enqueue_ev3_command", "action": "turn_to_color", "target_color": "R"},
    )
    controller.handle_message(
        "proto13/controller/controller-01/request",
        {"type": "enqueue_capture", "mode": "inventory_and_sort"},
    )
    by_topic = {topic: payload for topic, payload, _ in client.published if payload["type"] != "system_status"}
    assert by_topic["proto13/ev3/ev3-01/request"]["target_color"] == "R"
    assert by_topic["proto13/android/android-01/request"]["mode"] == "inventory_and_sort"
    assert controller.state == "busy"


def test_results_complete_commands_and_state_returns_to_ready():
    controller, client = make_controller()
    controller.handle_message(
        "proto13/controller/controller-01/request",
        {"type": "enqueue_ev3_command", "action": "advance_card"},
    )
    request_id = controller.ev3_queue.snapshot()["in_flight"]
    controller.handle_message(
        "proto13/ev3/ev3-01/status",
        {"type": "ev3_command_result", "request_id": request_id, "status": "complete"},
    )
    assert controller.state == "ready" and controller.ev3_queue.completed == 1


def test_android_retry_resends_and_success_completes():
    controller, client = make_controller()
    request_id = controller.android_queue.enqueue({"type": "capture_request", "mode": "sort_only"})
    controller.handle_message(
        "proto13/controller/controller-01/capture/result",
        {"type": "capture_result", "request_id": request_id, "status": "retry"},
    )
    sends = [p for t, p, _ in client.published if p["type"] == "capture_request"]
    assert len(sends) == 2
    controller.handle_message(
        "proto13/controller/controller-01/capture/result",
        {"type": "capture_result", "request_id": request_id, "status": "success", "card_name": "Bolt"},
    )
    assert controller.android_queue.depth == 0


def test_invalid_commands_are_rejected():
    controller, client = make_controller()
    controller.handle_message(
        "proto13/controller/controller-01/request",
        {"type": "enqueue_ev3_command", "action": "explode"},
    )
    controller.handle_message(
        "proto13/controller/controller-01/request",
        {"type": "enqueue_ev3_command", "action": "turn_to_color", "target_color": "X"},
    )
    assert controller.ev3_queue.depth == 0
