"""FastAPI server for mission control dashboard."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dashboard.state import build_case_state, read_artifact

STATIC_DIR = Path(__file__).resolve().parent / "static"
RING_BUFFER_SIZE = 500

_event_buffer: deque[dict[str, Any]] = deque(maxlen=RING_BUFFER_SIZE)
_subscribers: list[asyncio.Queue[dict[str, Any] | None]] = []
_default_case: str | None = None


class EventPayload(BaseModel):
    type: str
    ts: float | None = None

    model_config = {"extra": "allow"}


app = FastAPI(title="Legacy Modernization Agent — Monitoring")


@app.middleware("http")
async def disable_static_cache(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


def _broadcast(event: dict[str, Any]) -> None:
    for queue in list(_subscribers):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


@app.post("/events")
async def post_event(payload: EventPayload) -> dict[str, str]:
    event = payload.model_dump()
    if "ts" not in event or event["ts"] is None:
        event["ts"] = time.time()
    if "id" not in event:
        event["id"] = str(uuid.uuid4())
    _event_buffer.append(event)
    _broadcast(event)
    return {"status": "ok"}


@app.get("/events/stream")
async def events_stream() -> StreamingResponse:
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=100)
    _subscribers.append(queue)

    async def generate():
        try:
            for past in _event_buffer:
                yield f"data: {json.dumps(past, default=str)}\n\n"
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, default=str)}\n\n"
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/state")
async def api_state(case: str | None = Query(default=None)) -> dict[str, Any]:
    use_case = case or _default_case
    if not use_case:
        raise HTTPException(status_code=400, detail="case query parameter required")
    case_path = Path(__file__).resolve().parent.parent / "cases" / use_case
    if not case_path.is_dir():
        raise HTTPException(status_code=404, detail=f"case not found: {use_case}")
    return build_case_state(use_case)


@app.get("/api/artifact")
async def api_artifact(
    case: str = Query(...),
    name: str = Query(...),
) -> dict[str, str]:
    content = read_artifact(case, name)
    if content is None:
        raise HTTPException(status_code=404, detail="artifact not found or not previewable")
    return {"name": name, "content": content}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main(argv: list[str] | None = None) -> int:
    global _default_case
    parser = argparse.ArgumentParser(description="Mission control dashboard")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--case", help="Default case name for /api/state")
    args = parser.parse_args(argv)
    _default_case = args.case

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
