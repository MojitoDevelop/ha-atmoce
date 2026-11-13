"""Parse the observed MQTT dialect; commands follow the working Node-RED flow."""

import json
import math
import re
from typing import Any

from .const import CONTROL_OPTIONS

SERIAL_PATTERN = re.compile(r"[A-Z0-9_-]{1,64}")
MONITOR_PATTERN = re.compile(r"atmoce/gateway/([A-Z0-9_-]{1,64})/monitor")
MAX_PAYLOAD_BYTES = 65536
MONITOR_KEYS = {"solarGenerationPower", "batterySOC", "gridActivePower"}


def normalize_serial(value: str) -> str:
    """Validate a serial without allowing MQTT wildcards or path separators."""
    serial = value.strip().upper()
    if not SERIAL_PATTERN.fullmatch(serial):
        raise ValueError("Invalid serial number")
    return serial


def number(value: Any) -> float | None:
    """Only accept actual, finite JSON numbers (never booleans or strings)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except OverflowError:
        return None


def parse_monitor(topic: str, payload: str | bytes) -> tuple[str, dict[str, Any]]:
    """Validate identity and shape; missing individual fields stay unknown."""
    match = MONITOR_PATTERN.fullmatch(topic)
    if not match or len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("Invalid monitor message")
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError, RecursionError) as err:
        raise ValueError("Invalid JSON") from err
    serial = match[1]
    if not isinstance(data, dict) or data.get("sn") != serial:
        raise ValueError("Topic and payload serial numbers differ")
    if not any(number(data.get(key)) is not None for key in MONITOR_KEYS):
        raise ValueError("Not an Atmoce monitor payload")
    return serial, data


def sample_age(data: dict[str, Any], now: float) -> float | None:
    """Use systemTime (UTC), never the timezone-shifted systemLocalTime."""
    stamp = number(data.get("systemTime"))
    return None if stamp is None else now - stamp


def build_command(
    mode: str,
    power: float | None,
    target_soc: float | None,
    monitor: dict[str, Any],
) -> dict[str, int | float]:
    """Build only commands demonstrated in Node-RED, bounded by current limits."""
    if mode not in CONTROL_OPTIONS:
        raise ValueError("Unsupported control mode")
    command: dict[str, int | float] = {"batteryForcedControl": CONTROL_OPTIONS[mode]}
    if mode in ("automatic", "pause"):
        return command
    power = number(power)
    target_soc = number(target_soc)
    if power is None or power <= 0:
        raise ValueError("Power must be positive and finite")
    if target_soc is None or not 0 <= target_soc <= 100 or not target_soc.is_integer():
        raise ValueError("Target SOC must be a whole percentage between 0 and 100")
    limit = number(
        monitor.get("chargeMaxPower" if mode == "charge" else "dischargeMaxPower")
    )
    if limit is None or limit <= 0 or power > limit:
        raise ValueError(
            "Requested power exceeds the current device limit, or the limit is unknown"
        )
    power = round(power, 3)
    if power <= 0 or power > limit:
        raise ValueError("Power is outside device limits after MQTT rounding")
    soc = number(monitor.get("batterySOC"))
    if soc is None or not 0 <= soc <= 100:
        raise ValueError("Current battery SOC is unknown")
    if (mode == "charge" and soc >= target_soc) or (
        mode == "discharge" and soc <= target_soc
    ):
        # Exactly as in the flow: an already reached target returns to automatic.
        return {"batteryForcedControl": 2}
    command.update(
        batteryForcedMode=0,
        batteryForcedTargetSOC=int(target_soc),
        batteryForcedControlPower=round(power, 3),
    )
    return command
