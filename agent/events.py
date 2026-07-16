"""Fail-safe dashboard event emitter (stdlib only)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

_DEFAULT_URL = "http://localhost:8765/events"
_TIMEOUT_SEC = 0.5


def _dashboard_url() -> str:
    return os.environ.get("DASHBOARD_URL", _DEFAULT_URL).strip() or _DEFAULT_URL


def emit_event(event_type: str, **payload: Any) -> None:
    """POST an event to the mission-control dashboard; never raises."""
    body = json.dumps(
        {
            "type": event_type,
            "ts": time.time(),
            **payload,
        },
        default=str,
    ).encode("utf-8")
    req = urllib.request.Request(
        _dashboard_url(),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC):
            pass
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        pass
