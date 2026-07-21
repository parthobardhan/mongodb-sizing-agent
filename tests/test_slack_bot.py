"""Unit tests for Slack bot case discovery and watcher polling."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.continue_after_approval import ContinueResult
from slack_app.blocks import ACTION_APPROVE, case_action_value
from slack_app.bot import CaseWatcher, create_app, discover_cases

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PENDING_MODEL = """# Test case

**Approval status:** pending

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| FOO | anchor | `foo` |
"""


class ImmediateThread:
    """Run thread targets synchronously so async helpers are testable."""

    def __init__(self, target=None, daemon=None, args=(), kwargs=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        if self._target is not None:
            self._target(*self._args, **self._kwargs)


class FakeSlackApp:
    def __init__(self, token: str) -> None:
        self.token = token
        self.client = MagicMock()
        self.actions: dict[str, object] = {}

    def action(self, action_id: str):
        def deco(fn):
            self.actions[action_id] = fn
            return fn

        return deco


def test_discover_cases_returns_all_case_dirs():
    names = discover_cases()
    assert "_example" in names
    assert all(not name.startswith(".") for name in names)


def test_discover_cases_filter_single():
    names = discover_cases(case_filter="_example")
    assert names == ["_example"]


def test_discover_cases_filter_missing_raises():
    with pytest.raises(ValueError, match="case not found"):
        discover_cases(case_filter="_does_not_exist_xyz")


def test_case_watcher_posts_approval_for_any_pending_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    case_a = f"_pytest_slack_{uuid.uuid4().hex[:8]}_a"
    case_b = f"_pytest_slack_{uuid.uuid4().hex[:8]}_b"
    case_a_dir = tmp_path / "cases" / case_a
    case_b_dir = tmp_path / "cases" / case_b
    for case_dir in (case_a_dir, case_b_dir):
        outputs = case_dir / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "data-model.md").write_text(PENDING_MODEL, encoding="utf-8")
        (case_dir / "inputs").mkdir()
        (case_dir / "inputs" / "intake.json").write_text(
            json.dumps({"useCaseName": case_dir.name, "queryLatencySlaMs": 40}),
            encoding="utf-8",
        )

    cases_root = tmp_path / "cases"
    monkeypatch.setattr("slack_app.bot.CASES_ROOT", cases_root)
    monkeypatch.setattr(
        "slack_app.bot.case_dir_for",
        lambda name: cases_root / name,
    )

    client = MagicMock()
    client.chat_postMessage.side_effect = [
        {"ts": "111.111"},
        {"ts": "222.222"},
    ]
    watcher = CaseWatcher(channel_id="C_TEST", client=client, case_filter=None)
    watcher.poll_once()

    assert client.chat_postMessage.call_count == 2
    posted_texts = [call.kwargs.get("text") or call.args[0] for call in client.chat_postMessage.call_args_list]
    assert any(case_a in str(t) for t in posted_texts)
    assert any(case_b in str(t) for t in posted_texts)

    shutil.rmtree(tmp_path, ignore_errors=True)


def test_case_watcher_respects_case_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    case_a = f"_pytest_slack_{uuid.uuid4().hex[:8]}_a"
    case_b = f"_pytest_slack_{uuid.uuid4().hex[:8]}_b"
    for name in (case_a, case_b):
        case_dir = tmp_path / "cases" / name
        outputs = case_dir / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "data-model.md").write_text(PENDING_MODEL, encoding="utf-8")

    cases_root = tmp_path / "cases"
    monkeypatch.setattr("slack_app.bot.CASES_ROOT", cases_root)
    monkeypatch.setattr(
        "slack_app.bot.case_dir_for",
        lambda name: cases_root / name,
    )

    client = MagicMock()
    client.chat_postMessage.return_value = {"ts": "111.111"}
    watcher = CaseWatcher(channel_id="C_TEST", client=client, case_filter=case_a)
    watcher.poll_once()

    assert client.chat_postMessage.call_count == 1
    blocks = client.chat_postMessage.call_args.kwargs["blocks"]
    section = next(b for b in blocks if b.get("type") == "section")
    assert f"`{case_a}`" in section["text"]["text"]

    shutil.rmtree(tmp_path, ignore_errors=True)


def test_case_watcher_does_not_repost_same_mtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    case_name = f"_pytest_slack_{uuid.uuid4().hex[:8]}"
    case_dir = tmp_path / "cases" / case_name
    outputs = case_dir / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "data-model.md").write_text(PENDING_MODEL, encoding="utf-8")

    cases_root = tmp_path / "cases"
    monkeypatch.setattr("slack_app.bot.CASES_ROOT", cases_root)
    monkeypatch.setattr(
        "slack_app.bot.case_dir_for",
        lambda name: cases_root / name,
    )

    client = MagicMock()
    client.chat_postMessage.return_value = {"ts": "111.111"}
    watcher = CaseWatcher(channel_id="C_TEST", client=client, case_filter=case_name)

    watcher.poll_once()
    watcher.poll_once()

    assert client.chat_postMessage.call_count == 1

    shutil.rmtree(tmp_path, ignore_errors=True)


def _prepare_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    artifacts: tuple[str, ...] = (),
) -> str:
    case_name = f"_pytest_slack_{uuid.uuid4().hex[:8]}"
    case_dir = tmp_path / "cases" / case_name
    outputs = case_dir / "outputs"
    outputs.mkdir(parents=True)
    (case_dir / "inputs").mkdir()
    (case_dir / "inputs" / "intake.json").write_text(
        json.dumps({"useCaseName": case_name, "queryLatencySlaMs": 40}),
        encoding="utf-8",
    )
    (outputs / "data-model.md").write_text(PENDING_MODEL, encoding="utf-8")
    for name in artifacts:
        (outputs / name).write_text("{}", encoding="utf-8")

    cases_root = tmp_path / "cases"
    monkeypatch.setattr("slack_app.bot.CASES_ROOT", cases_root)
    monkeypatch.setattr("slack_app.bot.case_dir_for", lambda name: cases_root / name)
    return case_name


def _approve_body(case_name: str) -> dict:
    return {
        "user": {"username": "alice"},
        "channel": {"id": "C_TEST"},
        "message": {"ts": "111.222"},
        "actions": [{"value": case_action_value(case_name)}],
    }


def test_approve_with_artifacts_runs_tools_not_continue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case_name = _prepare_case(
        tmp_path,
        monkeypatch,
        artifacts=("seed.py", "mongodb_indexes.json", "sizing_inputs.json"),
    )
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")

    with patch("slack_bolt.App", FakeSlackApp):
        app, watcher = create_app("C_TEST", case_filter=case_name)

    handler = app.actions[ACTION_APPROVE]
    ack = MagicMock()

    with patch.object(watcher, "run_tools_async") as mock_tools:
        with patch.object(watcher, "run_continue_async") as mock_continue:
            with patch("slack_app.bot.emit_event"):
                handler(ack, _approve_body(case_name), app.client, MagicMock())

    ack.assert_called_once()
    mock_tools.assert_called_once_with(case_name, thread_ts="111.222")
    mock_continue.assert_not_called()
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_approve_with_missing_artifacts_runs_continue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case_name = _prepare_case(tmp_path, monkeypatch)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")

    with patch("slack_bolt.App", FakeSlackApp):
        app, watcher = create_app("C_TEST", case_filter=case_name)

    handler = app.actions[ACTION_APPROVE]
    ack = MagicMock()

    with patch.object(watcher, "run_tools_async") as mock_tools:
        with patch.object(watcher, "run_continue_async") as mock_continue:
            with patch("slack_app.bot.emit_event"):
                handler(ack, _approve_body(case_name), app.client, MagicMock())

    ack.assert_called_once()
    mock_continue.assert_called_once_with(
        case_name,
        thread_ts="111.222",
        approver="alice",
    )
    mock_tools.assert_not_called()
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_run_continue_async_no_session_posts_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case_name = _prepare_case(tmp_path, monkeypatch)
    client = MagicMock()
    watcher = CaseWatcher(channel_id="C_TEST", client=client, case_filter=case_name)

    with patch("slack_app.bot.threading.Thread", ImmediateThread):
        with patch(
            "slack_app.bot.continue_generate_after_approval",
            return_value=ContinueResult(
                status="no_session",
                error="Cannot resume: no session.json",
            ),
        ) as mock_continue:
            with patch.object(watcher, "run_tools_async") as mock_tools:
                watcher.run_continue_async(
                    case_name, "111.222", approver="alice"
                )

    mock_continue.assert_called_once()
    mock_tools.assert_not_called()
    texts = [
        call.kwargs.get("text", "")
        for call in client.chat_postMessage.call_args_list
    ]
    assert any("Resuming Cursor agent" in t for t in texts)
    assert any("no session.json" in t for t in texts)
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_run_continue_async_ok_then_runs_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case_name = _prepare_case(tmp_path, monkeypatch)
    client = MagicMock()
    watcher = CaseWatcher(channel_id="C_TEST", client=client, case_filter=case_name)

    with patch("slack_app.bot.threading.Thread", ImmediateThread):
        with patch(
            "slack_app.bot.continue_generate_after_approval",
            return_value=ContinueResult(status="ok", agent_id="agent-1"),
        ):
            with patch.object(watcher, "run_tools_async") as mock_tools:
                watcher.run_continue_async(
                    case_name, "111.222", approver="alice"
                )

    mock_tools.assert_called_once_with(case_name, "111.222")
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_run_continue_async_still_missing_posts_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case_name = _prepare_case(tmp_path, monkeypatch)
    client = MagicMock()
    watcher = CaseWatcher(channel_id="C_TEST", client=client, case_filter=case_name)

    with patch("slack_app.bot.threading.Thread", ImmediateThread):
        with patch(
            "slack_app.bot.continue_generate_after_approval",
            return_value=ContinueResult(
                status="still_missing",
                agent_id="agent-1",
                missing=["seed.py", "mongodb_indexes.json"],
            ),
        ):
            with patch.object(watcher, "run_tools_async") as mock_tools:
                watcher.run_continue_async(
                    case_name, "111.222", approver="alice"
                )

    mock_tools.assert_not_called()
    texts = [
        call.kwargs.get("text", "")
        for call in client.chat_postMessage.call_args_list
    ]
    assert any("seed.py" in t and "mongodb_indexes.json" in t for t in texts)
    shutil.rmtree(tmp_path, ignore_errors=True)
