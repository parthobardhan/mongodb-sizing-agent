"""Cursor SDK Agent/Run lifecycle."""

from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any

from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions, SendOptions

from agent.events import emit_event

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "auto"
STUCK_RUN_WAIT_TIMEOUT_SEC = 30.0

_HEADER_STATUS_RE = re.compile(
    r"^\*\*Approval status:\*\*\s*(approved|pending)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FOOTER_STATUS_RE = re.compile(
    r"^-\s*Status:\s*\*\*(approved|pending)\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _api_key() -> str:
    key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not key:
        raise CursorAgentError("CURSOR_API_KEY is not set")
    return key


def local_options() -> LocalAgentOptions:
    return LocalAgentOptions(
        cwd=str(PROJECT_ROOT),
        setting_sources=["project", "plugins"],
    )


def create_agent() -> Agent:
    """Create a local Cursor agent. Mode is applied per-send via SendOptions, not Agent.create."""
    return Agent.create(
        model=DEFAULT_MODEL,
        api_key=_api_key(),
        local=local_options(),
    )


def initial_send_mode(data_model_path: Path) -> str:
    """Plan until data-model.md is approved; agent mode afterward."""
    return "agent" if read_approval_status(data_model_path) == "approved" else "plan"


def _wait_run(run, *, timeout_sec: float) -> None:
    """Call run.wait() with a hard timeout so resume cannot hang forever."""
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(run.wait)
        try:
            future.result(timeout=timeout_sec)
        except FuturesTimeoutError as exc:
            raise TimeoutError(
                f"run.wait() timed out after {timeout_sec}s"
            ) from exc
    finally:
        # Do not wait for a stuck run.wait() thread — that would defeat the timeout.
        executor.shutdown(wait=False, cancel_futures=True)


def _recover_stuck_runs(
    agent_id: str,
    *,
    wait_timeout_sec: float = STUCK_RUN_WAIT_TIMEOUT_SEC,
) -> list[str]:
    """Cancel runs left in 'running' state (e.g. after a failed send)."""
    cancelled: list[str] = []
    try:
        runs = Agent.list_runs(agent_id)
    except CursorAgentError:
        return cancelled
    for item in runs:
        if getattr(item, "status", None) != "running":
            continue
        run_id = getattr(item, "id", None)
        if not run_id:
            continue
        try:
            run = Agent.get_run(run_id)
            if not run.supports("cancel"):
                print(
                    f"Skipping stuck run {run_id}: cancel not supported",
                    file=sys.stderr,
                )
                continue
            run.cancel()
            _wait_run(run, timeout_sec=wait_timeout_sec)
            cancelled.append(run_id)
        except (CursorAgentError, TimeoutError) as exc:
            print(f"Failed to recover run {run_id}: {exc}", file=sys.stderr)
            continue
    if cancelled:
        print(
            f"Recovered stuck run(s): {', '.join(cancelled)}",
            file=sys.stderr,
        )
    return cancelled


def resume_agent(agent_id: str) -> Agent:
    agent = Agent.resume(
        agent_id,
        AgentOptions(
            api_key=_api_key(),
            model=DEFAULT_MODEL,
            local=local_options(),
        ),
    )
    _recover_stuck_runs(agent_id)
    return agent


def _send_options(mode: str | None) -> SendOptions | None:
    if mode is None:
        return None
    return SendOptions(mode=mode, model=DEFAULT_MODEL)


def _tool_activity_details(message: Any) -> tuple[str, str] | None:
    """Return (tool_name, target) for tool-call style messages."""
    msg_type = getattr(message, "type", None)
    if msg_type not in ("tool_call", "tool-call", "tool", "function_call"):
        tool_name = getattr(message, "name", None) or getattr(message, "tool_name", None)
        if tool_name and msg_type not in ("assistant", "user", "system"):
            target = getattr(message, "path", None) or getattr(message, "target", None) or ""
            return tool_name, target
        return None

    name = (
        getattr(message, "name", None)
        or getattr(message, "tool_name", None)
        or getattr(getattr(message, "tool_call", None), "name", None)
        or "unknown"
    )
    target = (
        getattr(message, "path", None)
        or getattr(message, "target", None)
        or getattr(getattr(message, "args", None), "path", None)
        or ""
    )
    if not target and isinstance(getattr(message, "args", None), dict):
        target = message.args.get("path") or message.args.get("file") or ""
    return name, target


def _tool_activity_line(message: Any) -> str | None:
    """Return a short stderr line for tool-call / tool-result style messages."""
    details = _tool_activity_details(message)
    if not details:
        return None
    name, target = details
    suffix = f" {target}" if target else ""
    return f"[tool: {name}{suffix}]"


def stream_run_text(run) -> str:
    parts: list[str] = []
    for message in run.messages():
        details = _tool_activity_details(message)
        if details:
            name, target = details
            line = f"[tool: {name}{f' {target}' if target else ''}]"
            print(line, file=sys.stderr, flush=True)
            emit_event("tool_activity", tool=name, target=target, line=line)
        if getattr(message, "type", None) == "assistant":
            msg = getattr(message, "message", message)
            content = getattr(msg, "content", [])
            for block in content:
                if getattr(block, "type", None) == "text":
                    text = getattr(block, "text", "")
                    if text:
                        print(text, end="", flush=True)
                        parts.append(text)
                        emit_event("assistant_text", text=text)
                details = _tool_activity_details(block)
                if details:
                    name, target = details
                    line = f"[tool: {name}{f' {target}' if target else ''}]"
                    print(line, file=sys.stderr, flush=True)
                    emit_event("tool_activity", tool=name, target=target, line=line)
    return "".join(parts)


def send_and_wait(
    agent: Agent,
    user_input: str,
    *,
    mode: str | None = None,
) -> Any:
    opts = _send_options(mode)
    run = agent.send(user_input, opts) if opts else agent.send(user_input)
    print(f"[run id={run.id} agent={agent.agent_id}]", file=sys.stderr)
    emit_event(
        "run_started",
        run_id=run.id,
        agent_id=agent.agent_id,
        mode=mode,
    )
    stream_run_text(run)
    result = run.wait()
    emit_event(
        "run_finished",
        run_id=run.id,
        agent_id=agent.agent_id,
        status=result.status,
    )
    if result.status == "error":
        raise CursorAgentError(
            f"Agent run failed (run id={getattr(run, 'id', '?')} status=error)"
        )
    return result


def save_session(case_outputs: Path, agent_id: str, run_id: str | None = None) -> None:
    case_outputs.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"agent_id": agent_id}
    if run_id:
        payload["last_run_id"] = run_id
    (case_outputs / "session.json").write_text(json.dumps(payload, indent=2))


def load_session(case_outputs: Path) -> str | None:
    path = case_outputs / "session.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    return data.get("agent_id")


def read_approval_status(data_model_path: Path) -> str:
    if not data_model_path.is_file():
        return "missing"
    text = data_model_path.read_text(encoding="utf-8")
    header = _HEADER_STATUS_RE.search(text)
    if header:
        return header.group(1).lower()
    footer = _FOOTER_STATUS_RE.search(text)
    if footer:
        return footer.group(1).lower()
    return "unknown"
