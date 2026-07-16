"""Unit tests for Slack bot case discovery and watcher polling."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from slack_app.bot import CaseWatcher, discover_cases

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PENDING_MODEL = """# Test case

**Approval status:** pending

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| FOO | anchor | `foo` |
"""


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
