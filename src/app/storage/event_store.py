from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    direction TEXT NOT NULL,
    type TEXT,
    topic TEXT NOT NULL,
    request_id TEXT,
    device_id TEXT,
    status TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_request ON events(request_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
"""


class EventStore:
    """Append-only record of every MQTT message the controller sends or receives."""

    def __init__(self, path: str | Path = "data/proto13.db"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)

    def record(self, direction: str, topic: str, payload: dict[str, Any]) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO events (ts, direction, type, topic, request_id,"
                " device_id, status, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    direction,
                    payload.get("type"),
                    topic,
                    payload.get("request_id"),
                    payload.get("device_id"),
                    payload.get("status") or payload.get("state"),
                    json.dumps(payload),
                ),
            )

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._db.close()
