"""Unit tests for fail-safe dashboard event emitter."""

from __future__ import annotations

import socket
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agent.events import emit_event


class _CaptureHandler(BaseHTTPRequestHandler):
    received: list[bytes] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        type(self).received.append(body)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_emit_event_noop_when_dashboard_unreachable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DASHBOARD_URL", "http://127.0.0.1:1/events")
    emit_event("test_event", foo="bar")  # must not raise


def test_emit_event_posts_json(monkeypatch: pytest.MonkeyPatch):
    port = _free_port()
    _CaptureHandler.received = []
    server = HTTPServer(("127.0.0.1", port), _CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("DASHBOARD_URL", f"http://127.0.0.1:{port}/events")
        emit_event("pipeline_step", step="seed", status="ok")
        assert len(_CaptureHandler.received) == 1
        body = _CaptureHandler.received[0].decode("utf-8")
        assert '"type": "pipeline_step"' in body or '"type":"pipeline_step"' in body
        assert "seed" in body
    finally:
        server.shutdown()
