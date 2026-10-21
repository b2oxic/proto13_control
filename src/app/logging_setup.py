from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line; extra= fields are included as top-level keys."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        entry.update(
            {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        )
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = {
            k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS
        }
        suffix = " " + " ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
        time = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        return f"{time} {record.levelname:<7} {record.getMessage()}{suffix}"


def configure_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> None:
    root = logging.getLogger("proto13")
    root.setLevel(level)
    root.handlers.clear()
    root.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ConsoleFormatter())
    root.addHandler(console)

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        Path(log_dir) / "controller.jsonl",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)
