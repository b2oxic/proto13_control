from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .config.mqtt_settings import MqttConfig
from .config.mqtt_topics import status_topic
from .services.mqtt_service import MqttService
from .storage.event_store import EventStore

log = logging.getLogger("proto13.controller")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Controller:
    """Listens to the Proto13 topics, logs and stores everything, publishes status."""

    def __init__(
        self,
        service: MqttService,
        store: EventStore,
        config: MqttConfig | None = None,
    ):
        self.service = service
        self.store = store
        self.config = config or service.config
        self.mode = "sort_only"
        self.state = "starting"
        self.own_status_topic = status_topic("controller", self.config.controller_id)

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
        self._publish(self.own_status_topic, self._status_payload("ready"), retain=True)
        log.info("controller ready", extra={"controller_id": controller_id})

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
            self._answer_status_request(payload)
        elif message_type == "capture_result":
            log.info(
                "card recognised",
                extra={
                    "request_id": payload.get("request_id"),
                    "card_name": payload.get("card_name"),
                    "match_confidence": payload.get("match_confidence"),
                    "status": payload.get("status"),
                },
            )
        elif message_type == "ev3_command_result" and payload.get("status") == "failed":
            log.error(
                "EV3 command failed",
                extra={
                    "request_id": payload.get("request_id"),
                    "error": payload.get("error"),
                },
            )
        elif message_type not in {
            "capture_request",
            "ev3_command_result",
            "diagnostics_result",
            "system_status",
        }:
            log.warning("unknown message type", extra={"topic": topic, "type": message_type})

    def _answer_status_request(self, payload: dict[str, Any]) -> None:
        self._publish(
            self.own_status_topic,
            self._status_payload(self.state, request_id=payload.get("request_id")),
        )
