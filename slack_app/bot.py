"""Slack Socket Mode bot: approval request, approve button, sizing summary."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_ROOT = PROJECT_ROOT / "cases"
load_dotenv(PROJECT_ROOT / ".env")

from agent.approval import approve_data_model
from agent.continue_after_approval import continue_generate_after_approval
from agent.events import emit_event
from agent.session import read_approval_status
from agent.tools_runner import missing_tools_artifacts, run_tools_pipeline
from slack_app.blocks import (
    ACTION_APPROVE,
    ACTION_REQUEST_CHANGES,
    build_approval_request_blocks,
    build_approved_message_blocks,
    build_request_changes_blocks,
    build_sizing_summary_blocks,
    extract_disposition_summary,
    load_intake_sla,
    parse_case_action_value,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 2.0


def case_dir_for(use_case: str) -> Path:
    return CASES_ROOT / use_case


def discover_cases(*, case_filter: str | None = None) -> list[str]:
    """Return case folder names under cases/. When case_filter is set, return only that case."""
    if case_filter is not None:
        path = case_dir_for(case_filter)
        if not path.is_dir():
            raise ValueError(f"case not found: {path}")
        return [case_filter]

    if not CASES_ROOT.is_dir():
        return []

    names: list[str] = []
    for entry in sorted(CASES_ROOT.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            names.append(entry.name)
    return names


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_post_message(client: Any, **kwargs: Any) -> dict[str, Any] | None:
    try:
        return client.chat_postMessage(**kwargs)
    except Exception as exc:
        logger.warning("Slack chat_postMessage failed: %s", exc)
        return None


def _safe_update_message(client: Any, **kwargs: Any) -> None:
    try:
        client.chat_update(**kwargs)
    except Exception as exc:
        logger.warning("Slack chat_update failed: %s", exc)


def _safe_post_thread(client: Any, channel: str, thread_ts: str, text: str) -> None:
    _safe_post_message(client, channel=channel, thread_ts=thread_ts, text=text)


class CaseWatcher:
    """Poll case outputs and post Slack messages for approval and sizing."""

    def __init__(
        self,
        *,
        channel_id: str,
        client: Any,
        case_filter: str | None = None,
    ) -> None:
        self.channel_id = channel_id
        self.client = client
        self.case_filter = case_filter
        self._lock = threading.Lock()
        self._posted_approval_mtime: dict[str, float] = {}
        self._posted_sizing_mtime: dict[str, float] = {}
        self._approval_threads: dict[str, str] = {}

    def _watched_cases(self) -> list[str]:
        return discover_cases(case_filter=self.case_filter)

    def _data_model_path(self, case_name: str) -> Path:
        return case_dir_for(case_name) / "outputs" / "data-model.md"

    def _sizing_report_path(self, case_name: str) -> Path:
        return case_dir_for(case_name) / "outputs" / "sizing-report.json"

    def _file_mtime(self, path: Path) -> float | None:
        if not path.is_file():
            return None
        return path.stat().st_mtime

    def _maybe_post_approval_request(self, case_name: str) -> None:
        path = self._data_model_path(case_name)
        mtime = self._file_mtime(path)
        if mtime is None:
            return

        status = read_approval_status(path)
        if status != "pending":
            return

        with self._lock:
            if self._posted_approval_mtime.get(case_name) == mtime:
                return
            self._posted_approval_mtime[case_name] = mtime

        text = path.read_text(encoding="utf-8")
        case_dir = case_dir_for(case_name)
        intake = case_dir / "inputs" / "intake.json"
        use_case_display = case_name
        if intake.is_file():
            try:
                use_case_display = json.loads(intake.read_text())["useCaseName"]
            except (json.JSONDecodeError, KeyError, OSError):
                pass

        blocks = build_approval_request_blocks(
            case_name=case_name,
            use_case_display=use_case_display,
            disposition_lines=extract_disposition_summary(text),
            sla_ms=load_intake_sla(case_dir),
        )
        resp = _safe_post_message(
            self.client,
            channel=self.channel_id,
            text=f"Data model ready for approval: {use_case_display}",
            blocks=blocks,
        )
        if resp and resp.get("ts"):
            with self._lock:
                self._approval_threads[case_name] = resp["ts"]

    def _maybe_post_sizing_summary(self, case_name: str) -> None:
        path = self._sizing_report_path(case_name)
        mtime = self._file_mtime(path)
        if mtime is None:
            return

        with self._lock:
            if self._posted_sizing_mtime.get(case_name) == mtime:
                return
            self._posted_sizing_mtime[case_name] = mtime

        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read sizing report for %s: %s", case_name, exc)
            return

        blocks = build_sizing_summary_blocks(
            case_name=case_name,
            report=report,
            report_path=str(path.relative_to(PROJECT_ROOT)),
        )
        thread_ts = self._approval_threads.get(case_name)
        _safe_post_message(
            self.client,
            channel=self.channel_id,
            thread_ts=thread_ts,
            text=f"Sizing complete for {case_name}",
            blocks=blocks,
        )

    def poll_once(self) -> None:
        for case_name in self._watched_cases():
            self._maybe_post_approval_request(case_name)
            self._maybe_post_sizing_summary(case_name)

    def run_loop(self, stop_event: threading.Event) -> None:
        if self.case_filter:
            logger.info("Watching case %s (channel %s)", self.case_filter, self.channel_id)
        else:
            logger.info("Watching all cases under %s (channel %s)", CASES_ROOT, self.channel_id)
        while not stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                logger.exception("Watcher poll error: %s", exc)
            stop_event.wait(POLL_INTERVAL_SEC)

    def run_tools_async(self, case_name: str, thread_ts: str | None) -> None:
        def _run() -> None:
            case_dir = case_dir_for(case_name)
            if thread_ts:
                _safe_post_thread(
                    self.client,
                    self.channel_id,
                    thread_ts,
                    "Running tools pipeline (Docker → seed → indexes → sizing)…",
                )
            try:
                run_tools_pipeline(case_dir, no_cleanup=True)
                emit_event("pipeline_finished", case=case_name)
                if thread_ts:
                    _safe_post_thread(
                        self.client,
                        self.channel_id,
                        thread_ts,
                        "Tools pipeline finished. Sizing summary posting…",
                    )
                self._maybe_post_sizing_summary(case_name)
            except Exception as exc:
                logger.exception("Tools pipeline failed for %s: %s", case_name, exc)
                if thread_ts:
                    _safe_post_thread(
                        self.client,
                        self.channel_id,
                        thread_ts,
                        f"Tools pipeline failed: {exc}",
                    )

        threading.Thread(target=_run, daemon=True).start()

    def run_continue_async(
        self,
        case_name: str,
        thread_ts: str | None,
        *,
        approver: str,
    ) -> None:
        """Resume Cursor agent to generate Phase 5 artifacts, then run tools if ready."""

        def _run() -> None:
            case_dir = case_dir_for(case_name)
            if thread_ts:
                _safe_post_thread(
                    self.client,
                    self.channel_id,
                    thread_ts,
                    "Resuming Cursor agent in agent mode to generate Phase 5 artifacts…",
                )
            try:
                result = continue_generate_after_approval(
                    case_dir,
                    approver=approver,
                    use_case=case_name,
                )
            except Exception as exc:
                logger.exception(
                    "Agent continuation failed for %s: %s", case_name, exc
                )
                if thread_ts:
                    _safe_post_thread(
                        self.client,
                        self.channel_id,
                        thread_ts,
                        f"Agent continuation failed: {exc}",
                    )
                return

            if result.status == "no_session":
                if thread_ts:
                    _safe_post_thread(
                        self.client,
                        self.channel_id,
                        thread_ts,
                        result.error
                        or "Cannot resume Cursor agent: no session.json agent_id.",
                    )
                return

            if result.status == "error":
                if thread_ts:
                    _safe_post_thread(
                        self.client,
                        self.channel_id,
                        thread_ts,
                        f"Agent continuation failed: {result.error}",
                    )
                return

            if result.status == "still_missing":
                names = ", ".join(result.missing)
                if thread_ts:
                    _safe_post_thread(
                        self.client,
                        self.channel_id,
                        thread_ts,
                        f"Generate artifacts still missing after agent run: {names}. "
                        "Fix generation or re-approve once files exist.",
                    )
                return

            self.run_tools_async(case_name, thread_ts)

        threading.Thread(target=_run, daemon=True).start()


def create_app(channel_id: str, *, case_filter: str | None = None) -> tuple[Any, CaseWatcher]:
    from slack_bolt import App

    bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("SLACK_BOT_TOKEN is not set")

    app = App(token=bot_token)
    watcher = CaseWatcher(
        channel_id=channel_id,
        client=app.client,
        case_filter=case_filter,
    )

    def _resolve_case(body: dict[str, Any]) -> str | None:
        actions = body.get("actions") or []
        if not actions:
            return case_filter
        return parse_case_action_value(actions[0].get("value")) or case_filter

    def _user_name(body: dict[str, Any]) -> str:
        user = body.get("user") or {}
        return user.get("username") or user.get("name") or user.get("id") or "unknown"

    @app.action(ACTION_APPROVE)
    def handle_approve(ack, body, client, logger):  # noqa: ARG001
        ack()
        resolved_case = _resolve_case(body)
        if not resolved_case:
            logger.warning("Approve ignored: could not resolve case from button")
            return
        approver = _user_name(body)
        case_dir = case_dir_for(resolved_case)
        data_model_path = case_dir / "outputs" / "data-model.md"

        try:
            status = approve_data_model(data_model_path, approver)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("Approve failed: %s", exc)
            return

        stamp = _utc_now_iso()
        emit_event("approval_changed", case=resolved_case, status=status, via="slack")

        channel = body["channel"]["id"]
        message = body["message"]
        ts = message["ts"]

        _safe_update_message(
            client,
            channel=channel,
            ts=ts,
            text=f"Approved by {approver}",
            blocks=build_approved_message_blocks(approver=approver, approved_at=stamp),
        )

        with watcher._lock:
            watcher._approval_threads[resolved_case] = ts

        missing = missing_tools_artifacts(case_dir)
        if not missing:
            watcher.run_tools_async(resolved_case, thread_ts=ts)
        else:
            watcher.run_continue_async(
                resolved_case,
                thread_ts=ts,
                approver=approver,
            )

    @app.action(ACTION_REQUEST_CHANGES)
    def handle_request_changes(ack, body, client, logger):  # noqa: ARG001
        ack()
        requester = _user_name(body)
        channel = body["channel"]["id"]
        message = body["message"]
        ts = message["ts"]

        _safe_update_message(
            client,
            channel=channel,
            ts=ts,
            text=f"Changes requested by {requester}",
            blocks=build_request_changes_blocks(requester=requester),
        )
        _safe_post_thread(
            client,
            channel,
            ts,
            "Please reply in this thread with what should change in the data model.",
        )

    return app, watcher


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Slack approval bot (Socket Mode)")
    parser.add_argument(
        "--case",
        help="Watch only this case folder (default: all directories under cases/)",
    )
    parser.add_argument("--channel", help="Slack channel ID (or SLACK_CHANNEL_ID)")
    args = parser.parse_args(argv)

    channel_id = (args.channel or os.environ.get("SLACK_CHANNEL_ID", "")).strip()
    if not channel_id:
        print("error: set SLACK_CHANNEL_ID or pass --channel", file=sys.stderr)
        return 1

    app_token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    if not app_token:
        print("error: SLACK_APP_TOKEN is not set", file=sys.stderr)
        return 1

    try:
        discover_cases(case_filter=args.case)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    from slack_bolt.adapter.socket_mode import SocketModeHandler

    bolt_app, watcher = create_app(channel_id, case_filter=args.case)
    stop_event = threading.Event()
    watcher_thread = threading.Thread(
        target=watcher.run_loop,
        args=(stop_event,),
        daemon=True,
    )
    watcher_thread.start()

    if args.case:
        logger.info("Starting Slack Socket Mode handler for case %s", args.case)
    else:
        logger.info("Starting Slack Socket Mode handler (all cases)")
    try:
        SocketModeHandler(bolt_app, app_token).start()
    except KeyboardInterrupt:
        stop_event.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
