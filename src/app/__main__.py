from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from uuid import uuid4

from .config.mqtt_settings import MqttConfig
from .config.mqtt_topics import QUEUE_ACTIONS, component_request_topic
from .controller import Controller
from .logging_setup import configure_logging
from .services.mqtt_service import MqttService
from .storage.event_store import EventStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Proto13 controller")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run", help="Run the controller until interrupted")
    run.add_argument("--log-dir", default="logs")
    run.add_argument("--db", default="data/proto13.db")
    send_command = commands.add_parser(
        "send-ev3-command", help="Send a sorting command to the EV3"
    )
    send_command.add_argument("action", choices=QUEUE_ACTIONS.values())
    send_command.add_argument("--device-id", help="Target EV3 device ID")
    send_command.add_argument("--sequence", type=int, default=1)
    send_command.add_argument("--target-color", choices=("W", "U", "B", "R", "G", "M"))
    send_command.add_argument("--degrees", type=int)
    send_command.add_argument("--card-id")
    return parser


def _build_ev3_queue_command(
    device_id: str,
    action: str,
    sequence: int,
    target_color: str | None,
    degrees: int | None,
    card_id: str | None,
) -> dict[str, str | int | None]:
    return {
        "type": "ev3_queue_command",
        "request_id": str(uuid4()),
        "device_id": device_id,
        "sequence": sequence,
        "action": action,
        "target_color": target_color,
        "degrees": degrees,
        "card_id": card_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _run_controller(log_dir: str, db_path: str) -> None:
    configure_logging(log_dir)
    store = EventStore(db_path)
    controller = Controller(MqttService(), store)
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        store.close()


def main() -> None:
    """App entry point for the MQTT service.

    This is the correct module entry point for the project and can be launched
    with: python -m src.app
    """
    args = _build_parser().parse_args()
    if args.command == "run":
        _run_controller(args.log_dir, args.db)
        return
    if args.command != "send-ev3-command":
        print("Proto13 controller entry point loaded.")
        print(f"MQTT service configured: {MqttService.__name__}")
        return

    config = MqttConfig.from_environment()
    service = MqttService(config=config)
    device_id = args.device_id or config.ev3_device_id
    request_topic = component_request_topic("ev3", device_id)
    payload = _build_ev3_queue_command(
        device_id=device_id,
        action=args.action,
        sequence=args.sequence,
        target_color=args.target_color,
        degrees=args.degrees,
        card_id=args.card_id,
    )

    try:
        service.connect()
        result = service.publish(request_topic, payload)
        result.wait_for_publish(timeout=10)
        if not result.is_published():
            raise TimeoutError("MQTT message was not delivered within 10 seconds.")
        print(f"Published {args.action} request to {request_topic}")
    finally:
        service.disconnect()


if __name__ == "__main__":
    main()
