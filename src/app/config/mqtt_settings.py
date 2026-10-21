from __future__ import annotations

import os
from dataclasses import dataclass

from .mqtt_topics import component_request_topic


@dataclass(frozen=True)
class MqttConfig:
    broker_host: str = "192.168.0.55"
    broker_port: int = 1883
    client_id: str = "proto13_control"
    username: str | None = None
    password: str | None = None
    ev3_device_id: str = "ev3-01"
    controller_id: str = "controller-01"
    keepalive: int = 60

    @property
    def ev3_request_topic(self) -> str:
        return component_request_topic("ev3", self.ev3_device_id)

    @classmethod
    def from_environment(cls) -> MqttConfig:
        return cls(
            broker_host=os.getenv("MQTT_BROKER_HOST", "192.168.0.55"),
            broker_port=int(os.getenv("MQTT_BROKER_PORT", "1883")),
            client_id=os.getenv("MQTT_CLIENT_ID", "proto13_control"),
            username=os.getenv("MQTT_USERNAME") or None,
            password=os.getenv("MQTT_PASSWORD") or None,
            ev3_device_id=os.getenv("MQTT_EV3_DEVICE_ID", "ev3-01"),
            controller_id=os.getenv("MQTT_CONTROLLER_ID", "controller-01"),
            keepalive=int(os.getenv("MQTT_KEEPALIVE", "60")),
        )