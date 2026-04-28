"""Shared parser for wired hardware telemetry messages.

The firmware can keep the current text protocol during the first wired
iteration. This parser centralizes the message shapes so the UI does not need
to care whether data came from serial, UDP, or a future bridge.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Optional


EVENT_MESSAGES = {"pain", "pain2", "highdamp", "lowdamp", "keep"}
POSITION_PREFIXES = ("pos:", "pull:", "dist:")


@dataclass(frozen=True)
class HardwareMessage:
    """Normalized message sent by the mannequin hardware."""

    kind: str
    raw: str
    value: Optional[float] = None
    event: Optional[str] = None
    sequence: Optional[str] = None


def _try_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(payload: dict, keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def parse_hardware_message(message: str) -> HardwareMessage:
    """Parse one hardware line into a small normalized object.

    Supported text examples:
    - ``SEQ:pain,pain2,highdamp,lowdamp``
    - ``POS:12.5`` / ``PULL:12.5`` / ``DIST:12.5``
    - ``SPEED:3.2``
    - ``Pain`` / ``Pain2`` / ``HighDamp`` / ``LowDamp`` / ``Keep``

    A JSON line is also accepted for later firmware versions, for example:
    ``{"type":"telemetry","position_cm":12.5,"speed_cmps":3.2}``
    """

    raw = (message or "").strip()
    lowered = raw.lower()

    if not raw:
        return HardwareMessage(kind="empty", raw=raw)

    if lowered.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return HardwareMessage(kind="unknown", raw=raw)

        event = payload.get("event") or payload.get("type")
        position = _try_float(_first_present(payload, ("position_cm", "pos", "distance_cm")))
        speed = _try_float(_first_present(payload, ("speed_cmps", "speed")))

        if position is not None:
            return HardwareMessage(kind="position", raw=raw, value=position, event=event)
        if speed is not None:
            return HardwareMessage(kind="speed", raw=raw, value=speed, event=event)
        if event:
            event_text = str(event).strip()
            return HardwareMessage(kind="event", raw=raw, event=event_text)
        return HardwareMessage(kind="json", raw=raw)

    if lowered.startswith("seq:"):
        return HardwareMessage(kind="sequence", raw=raw, sequence=raw.split(":", 1)[1].strip())

    if lowered.startswith(POSITION_PREFIXES):
        return HardwareMessage(kind="position", raw=raw, value=_try_float(raw.split(":", 1)[1]))

    if lowered.startswith("speed:"):
        return HardwareMessage(kind="speed", raw=raw, value=_try_float(raw.split(":", 1)[1]))

    if lowered in EVENT_MESSAGES:
        return HardwareMessage(kind="event", raw=raw, event=lowered)

    return HardwareMessage(kind="unknown", raw=raw)
