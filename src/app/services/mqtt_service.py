from __future__ import annotations

import json
from dataclasses import dataclass
from threading import Event
from typing import Any

from ..config.mqtt_settings import MqttConfig


@dataclass
class MqttMessage:
    topic: str
    payload: dict[str, Any]
    qos: int = 1


class MqttService:
    def __init__(self, client: Any | None = None, config: MqttConfig | None = None):
        self.client = client
        self.config = config or MqttConfig.from_environment()
        self._connected_event = Event()
        self._connection_error: str | None = None

    def connect(self) -> None:
        if self.client is None:
            import paho.mqtt.client as mqtt

            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.config.client_id,
            )
            if self.config.username:
                self.client.username_pw_set(self.config.username, self.config.password)

        self._connected_event.clear()
        self._connection_error = None
        self.client.on_connect = self._on_connect
        self.client.connect(
            self.config.broker_host,
            self.config.broker_port,
            self.config.keepalive,
        )
        self.client.loop_start()
        if not self._connected_event.wait(timeout=10):
            self.disconnect()
            raise TimeoutError("MQTT broker connection was not confirmed within 10 seconds.")
        if self._connection_error is not None:
            connection_error = self._connection_error
            self.disconnect()
            raise ConnectionError(f"MQTT broker rejected the connection: {connection_error}")

    def _on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if reason_code != 0:
            self._connection_error = str(reason_code)
        self._connected_event.set()

    def publish(self, topic: str, payload: dict[str, Any], qos: int = 1) -> Any:
        if self.client is None:
            raise RuntimeError("MQTT client is not configured.")
        return self.client.publish(topic, json.dumps(payload), qos=qos)

    def subscribe(self, topic: str) -> None:
        if self.client is None:
            raise RuntimeError("MQTT client is not configured.")
        self.client.subscribe(topic)

    def disconnect(self) -> None:
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
