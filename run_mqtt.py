#!/usr/bin/env python3
"""Bootstrap the Proto13 controller.

Ensures the MQTT dependency is installed, then launches the app using the
module entry point defined in src/app/__main__.py.
"""

from __future__ import annotations

import importlib.util
import runpy
import subprocess
import sys

REQUIRED_PACKAGE = "paho-mqtt"


def ensure_mqtt_dependency() -> None:
    """Install paho-mqtt if it is not already available."""
    if importlib.util.find_spec("paho") is not None:
        return

    print(f"{REQUIRED_PACKAGE} is not installed. Installing it now...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "paho-mqtt>=2.0.0"],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def main() -> None:
    ensure_mqtt_dependency()
    if len(sys.argv) == 1:
        sys.argv.append("run")
    print("Launching Proto13 controller entry point...")
    runpy.run_module("src.app", run_name="__main__")


if __name__ == "__main__":
    main()

