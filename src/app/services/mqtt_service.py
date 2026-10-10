from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MqttMessage:
    topic: str
    payload: dict[str, Any]
    qos: int = 1


class MqttService:
    def __init__(self, client: Any | None = None):
        self.client = client

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if self.client is None:
            raise RuntimeError("MQTT client is not configured.")
        self.client.publish(topic, payload)

    def subscribe(self, topic: str) -> None:
        if self.client is None:
            raise RuntimeError("MQTT client is not configured.")
        self.client.subscribe(topic)
