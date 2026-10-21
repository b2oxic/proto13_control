from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

log = logging.getLogger("proto13.queue")


@dataclass
class QueuedCommand:
    request_id: str
    payload: dict[str, Any]
    attempts: int = 0
    deadline: float = 0.0


class DeviceQueue:
    """FIFO command queue for one device; only one command is in flight at a time.

    The in-flight command is resent if the device does not answer before the
    timeout. After max_retries resends the command is dropped and the queue
    faults, pausing until resume() so hardware is never driven blindly.
    """

    def __init__(
        self,
        name: str,
        device_id: str,
        topic: str,
        publish: Callable[[str, dict[str, Any]], None],
        timeout: float = 30.0,
        max_retries: int = 2,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.name = name
        self.device_id = device_id
        self.topic = topic
        self._publish = publish
        self.timeout = timeout
        self.max_retries = max_retries
        self._clock = clock
        self._lock = threading.RLock()
        self._pending: deque[QueuedCommand] = deque()
        self._inflight: QueuedCommand | None = None
        self.paused = False
        self.faulted = False
        self._sequence = 0
        self.completed = 0
        self.failed = 0

    def enqueue(self, payload: dict[str, Any]) -> str:
        with self._lock:
            payload = dict(payload)
            request_id = payload.get("request_id") or str(uuid4())
            payload["request_id"] = request_id
            payload["device_id"] = self.device_id
            if self.name == "ev3":
                self._sequence += 1
                payload.setdefault("sequence", self._sequence)
            self._pending.append(QueuedCommand(request_id, payload))
            log.info(
                "queued",
                extra={"queue": self.name, "request_id": request_id, "depth": self.depth},
            )
            self._pump()
            return request_id

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._pending) + (1 if self._inflight else 0)

    def owns(self, request_id: str | None) -> bool:
        with self._lock:
            return (
                self._inflight is not None and self._inflight.request_id == request_id
            )

    def progress(self, request_id: str | None) -> None:
        """Device acknowledged or is working on the command; restart the timeout."""
        with self._lock:
            if self.owns(request_id):
                self._inflight.deadline = self._clock() + self.timeout

    def complete(self, request_id: str | None) -> None:
        with self._lock:
            if not self.owns(request_id):
                return
            self._inflight = None
            self.completed += 1
            log.info("command complete", extra={"queue": self.name, "request_id": request_id})
            self._pump()

    def fail(self, request_id: str | None, error: str | None = None) -> None:
        with self._lock:
            if not self.owns(request_id):
                return
            self._retry_or_fault(error or "device reported failure")

    def tick(self) -> None:
        with self._lock:
            if self._inflight and self._clock() >= self._inflight.deadline:
                self._retry_or_fault("timed out waiting for device")
            self._pump()

    def pause(self) -> None:
        with self._lock:
            self.paused = True
            log.info("queue paused", extra={"queue": self.name})

    def resume(self) -> None:
        with self._lock:
            self.paused = False
            self.faulted = False
            log.info("queue resumed", extra={"queue": self.name})
            self._pump()

    def clear(self) -> int:
        with self._lock:
            dropped = len(self._pending)
            self._pending.clear()
            log.info("queue cleared", extra={"queue": self.name, "dropped": dropped})
            return dropped

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "device_id": self.device_id,
                "pending": len(self._pending),
                "in_flight": self._inflight.request_id if self._inflight else None,
                "paused": self.paused,
                "faulted": self.faulted,
                "completed": self.completed,
                "failed": self.failed,
            }

    def _retry_or_fault(self, reason: str) -> None:
        command = self._inflight
        if command.attempts <= self.max_retries:
            log.warning(
                "retrying command",
                extra={
                    "queue": self.name,
                    "request_id": command.request_id,
                    "attempt": command.attempts,
                    "reason": reason,
                },
            )
            self._send(command)
            return
        self._inflight = None
        self.failed += 1
        self.faulted = True
        self.paused = True
        log.error(
            "command failed; queue faulted",
            extra={"queue": self.name, "request_id": command.request_id, "reason": reason},
        )

    def _pump(self) -> None:
        if self.paused or self._inflight or not self._pending:
            return
        command = self._pending.popleft()
        self._inflight = command
        self._send(command)

    def _send(self, command: QueuedCommand) -> None:
        command.attempts += 1
        command.deadline = self._clock() + self.timeout
        command.payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._publish(self.topic, command.payload)
