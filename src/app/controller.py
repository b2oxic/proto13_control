from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .config.mqtt_settings import MqttConfig
from .config.mqtt_topics import (
    MODE_CONFIG,
    QUEUE_ACTIONS,
    component_request_topic,
    status_topic,
)
from .queues import DeviceQueue
from .services.mqtt_service import MqttService
from .storage.event_store import EventStore

log = logging.getLogger("proto13.controller")

COLORS = {"W", "U", "B", "R", "G", "M"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Controller:
    """Listens to the Proto13 topics, runs the EV3/Android queues, logs everything."""

    def __init__(
        self,
        service: MqttService,
        store: EventStore,
        config: MqttConfig | None = None,
        queue_timeout: float = 30.0,
        max_retries: int = 2,
    ):
        self.service = service
        self.store = store
        self.config = config or service.config
        self.mode = "sort_only"
        self.state = "starting"
        self.own_status_topic = status_topic("controller", self.config.controller_id)
        self.ev3_queue = DeviceQueue(
            "ev3",
            self.config.ev3_device_id,
            component_request_topic("ev3", self.config.ev3_device_id),
            self._publish,
            timeout=queue_timeout,
            max_retries=max_retries,
        )
        self.android_queue = DeviceQueue(
            "android",
            self.config.android_device_id,
            component_request_topic("android", self.config.android_device_id),
            self._publish,
            timeout=queue_timeout,
            max_retries=max_retries,
        )
        self.queues = (self.ev3_queue, self.android_queue)

    def _status_payload(
        self, state: str, online: bool = True, request_id: str | None = None
    ) -> dict[str, Any]:
        return {
            "type": "system_status",
            "request_id": request_id,
            "device_id": self.config.controller_id,
            "online": online,
            "state": state,
            "mode": self.mode,
            "queues": {q.name: q.snapshot() for q in self.queues},
            "timestamp": _now(),
        }

    def _publish(
        self, topic: str, payload: dict[str, Any], retain: bool = False
    ) -> None:
        self.service.publish(topic, payload, retain=retain)
        self.store.record("out", topic, payload)
        log.info(
            "published %s", payload.get("type"),
            extra={"topic": topic, "request_id": payload.get("request_id")},
        )

    def _publish_status(self, request_id: str | None = None) -> None:
        self._publish(
            self.own_status_topic,
            self._status_payload(self.state, request_id=request_id),
            retain=True,
        )

    def _compute_state(self) -> str:
        if any(q.faulted for q in self.queues):
            return "degraded"
        if any(q.depth for q in self.queues):
            return "busy"
        return "ready"

    def _refresh_state(self) -> None:
        state = self._compute_state()
        if state != self.state:
            self.state = state
            self._publish_status()

    def start(self) -> None:
        self.service.set_will(
            self.own_status_topic, self._status_payload("fault", online=False)
        )
        self.service.set_message_handler(self.handle_message)
        self.service.connect()
        controller_id = self.config.controller_id
        self.service.subscribe(f"proto13/controller/{controller_id}/#")
        self.service.subscribe("proto13/+/+/status")
        self.state = "ready"
        self._publish_status()
        log.info("controller ready", extra={"controller_id": controller_id})

    def tick(self) -> None:
        """Call about once a second: enforces command timeouts and retries."""
        for queue in self.queues:
            queue.tick()
        self._refresh_state()

    def stop(self) -> None:
        self.state = "fault"
        try:
            self._publish(
                self.own_status_topic,
                self._status_payload("fault", online=False),
                retain=True,
            )
        finally:
            self.service.disconnect()

    def handle_message(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == self.own_status_topic:
            return
        self.store.record("in", topic, payload)
        message_type = payload.get("type")
        log.info(
            "received %s", message_type,
            extra={
                "topic": topic,
                "request_id": payload.get("request_id"),
                "device_id": payload.get("device_id"),
            },
        )

        if message_type in {"run_status_check", "run_diagnostics"}:
            self._publish_status(request_id=payload.get("request_id"))
        elif message_type in CONTROL_HANDLERS:
            getattr(self, CONTROL_HANDLERS[message_type])(payload)
        elif message_type == "capture_result":
            self._handle_capture_result(payload)
        elif message_type == "ev3_command_result":
            self._handle_ev3_result(payload)
        elif message_type not in {
            "capture_request",
            "diagnostics_result",
            "system_status",
        }:
            log.warning("unknown message type", extra={"topic": topic, "type": message_type})
        self._refresh_state()

    def _handle_capture_result(self, payload: dict[str, Any]) -> None:
        request_id = payload.get("request_id")
        status = payload.get("status")
        log.info(
            "card recognised",
            extra={
                "request_id": request_id,
                "card_name": payload.get("card_name"),
                "match_confidence": payload.get("match_confidence"),
                "status": status,
            },
        )
        if status == "success":
            self.android_queue.complete(request_id)
        elif status == "retry":
            self.android_queue.fail(request_id, "recognition asked for retry")
        else:
            self.android_queue.fail(request_id, "recognition failed")

    def _handle_ev3_result(self, payload: dict[str, Any]) -> None:
        request_id = payload.get("request_id")
        status = payload.get("status")
        if status in {"accepted", "in_progress"}:
            self.ev3_queue.progress(request_id)
        elif status == "complete":
            self.ev3_queue.complete(request_id)
        elif status == "failed":
            log.error(
                "EV3 command failed",
                extra={"request_id": request_id, "error": payload.get("error")},
            )
            self.ev3_queue.fail(request_id, payload.get("error"))

    def _enqueue_ev3_command(self, payload: dict[str, Any]) -> None:
        action = payload.get("action")
        color = payload.get("target_color")
        if action not in QUEUE_ACTIONS.values() or (color is not None and color not in COLORS):
            log.warning("rejected EV3 command", extra={"action": action, "target_color": color})
            return
        self.ev3_queue.enqueue(
            {
                "type": "ev3_queue_command",
                "request_id": payload.get("request_id"),
                "action": action,
                "target_color": color,
                "degrees": payload.get("degrees"),
                "card_id": payload.get("card_id"),
            }
        )

    def _enqueue_capture(self, payload: dict[str, Any]) -> None:
        mode = payload.get("mode") or self.mode
        if mode not in MODE_CONFIG.values():
            log.warning("rejected capture request", extra={"mode": mode})
            return
        self.android_queue.enqueue(
            {
                "type": "capture_request",
                "request_id": payload.get("request_id"),
                "mode": mode,
                "requested_at": _now(),
            }
        )

    def _set_mode(self, payload: dict[str, Any]) -> None:
        mode = payload.get("mode")
        if mode not in MODE_CONFIG.values():
            log.warning("rejected mode change", extra={"mode": mode})
            return
        self.mode = mode
        self._publish_status()

    def _pause_queues(self, payload: dict[str, Any]) -> None:
        for queue in self.queues:
            queue.pause()
        self._publish_status()

    def _resume_queues(self, payload: dict[str, Any]) -> None:
        for queue in self.queues:
            queue.resume()
        self._publish_status()

    def _clear_queues(self, payload: dict[str, Any]) -> None:
        for queue in self.queues:
            queue.clear()
        self._publish_status()


CONTROL_HANDLERS = {
    "enqueue_ev3_command": "_enqueue_ev3_command",
    "enqueue_capture": "_enqueue_capture",
    "set_mode": "_set_mode",
    "pause_queues": "_pause_queues",
    "resume_queues": "_resume_queues",
    "clear_queues": "_clear_queues",
}
