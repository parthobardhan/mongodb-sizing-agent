"""Unit tests for post-approval Cursor agent continuation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.continue_after_approval import (
    build_continue_prompt,
    continue_generate_after_approval,
)


def _write_case(
    tmp_path: Path,
    *,
    with_session: bool = True,
    with_legacy: bool = False,
    artifacts: tuple[str, ...] = (),
) -> Path:
    case_dir = tmp_path / "cases" / "settlement"
    inputs = case_dir / "inputs"
    outputs = case_dir / "outputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps({"useCaseName": "settlement", "queryLatencySlaMs": 40}),
        encoding="utf-8",
    )
    if with_session:
        (outputs / "session.json").write_text(
            json.dumps({"agent_id": "agent-xyz"}),
            encoding="utf-8",
        )
    if with_legacy:
        legacy = inputs / "legacy"
        legacy.mkdir()
        (legacy / "Dao.java").write_text("class Dao {}", encoding="utf-8")
    for name in artifacts:
        (outputs / name).write_text("{}", encoding="utf-8")
    return case_dir


def test_build_continue_prompt_includes_approver_and_phase5_only(tmp_path: Path):
    case_dir = _write_case(tmp_path)
    prompt = build_continue_prompt(
        use_case="settlement",
        approver="alice",
        case_dir=case_dir,
    )
    assert "alice" in prompt
    assert "settlement" in prompt
    assert "already approved" in prompt
    assert "seed.py" in prompt
    assert "mongodb_indexes.json" in prompt
    assert "run_local_stack" in prompt
    assert "apply_indexes.py" in prompt
    assert "size_from_dbstats.py" in prompt
    assert "Do NOT" in prompt
    assert "mongo_repository.py" not in prompt


def test_build_continue_prompt_includes_legacy_when_present(tmp_path: Path):
    case_dir = _write_case(tmp_path, with_legacy=True)
    prompt = build_continue_prompt(
        use_case="settlement",
        approver="bob",
        case_dir=case_dir,
    )
    assert "mongo_repository.py" in prompt
    assert "test_mongo_repository.py" in prompt


def test_continue_missing_session_does_not_resume(tmp_path: Path):
    case_dir = _write_case(tmp_path, with_session=False)
    with patch("agent.continue_after_approval.resume_agent") as mock_resume:
        with patch("agent.continue_after_approval.send_and_wait") as mock_send:
            result = continue_generate_after_approval(case_dir, approver="alice")

    assert result.status == "no_session"
    assert result.error is not None
    assert "session.json" in result.error
    mock_resume.assert_not_called()
    mock_send.assert_not_called()


def test_continue_resumes_and_sends_in_agent_mode(tmp_path: Path):
    case_dir = _write_case(tmp_path)
    mock_agent = MagicMock()
    mock_agent.agent_id = "agent-xyz"
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)

    with patch(
        "agent.continue_after_approval.resume_agent", return_value=mock_agent
    ) as mock_resume:
        with patch("agent.continue_after_approval.send_and_wait") as mock_send:
            with patch(
                "agent.continue_after_approval.missing_tools_artifacts",
                return_value=[],
            ):
                result = continue_generate_after_approval(case_dir, approver="alice")

    assert result.status == "ok"
    assert result.agent_id == "agent-xyz"
    mock_resume.assert_called_once_with("agent-xyz")
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] is mock_agent
    assert "alice" in args[1]
    assert kwargs["mode"] == "agent"
    mock_agent.__enter__.assert_called_once()
    mock_agent.__exit__.assert_called_once()


def test_continue_still_missing_after_send(tmp_path: Path):
    case_dir = _write_case(tmp_path)
    mock_agent = MagicMock()
    mock_agent.agent_id = "agent-xyz"
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    missing = [case_dir / "outputs" / "seed.py"]

    with patch(
        "agent.continue_after_approval.resume_agent", return_value=mock_agent
    ):
        with patch("agent.continue_after_approval.send_and_wait"):
            with patch(
                "agent.continue_after_approval.missing_tools_artifacts",
                return_value=missing,
            ):
                result = continue_generate_after_approval(case_dir, approver="alice")

    assert result.status == "still_missing"
    assert result.missing == ["seed.py"]


def test_continue_sdk_error_returns_error_status(tmp_path: Path):
    case_dir = _write_case(tmp_path)
    mock_agent = MagicMock()
    mock_agent.agent_id = "agent-xyz"
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)

    with patch(
        "agent.continue_after_approval.resume_agent", return_value=mock_agent
    ):
        with patch(
            "agent.continue_after_approval.send_and_wait",
            side_effect=RuntimeError("SDK boom"),
        ):
            result = continue_generate_after_approval(case_dir, approver="alice")

    assert result.status == "error"
    assert "SDK boom" in (result.error or "")
    assert result.agent_id == "agent-xyz"


def test_continue_saves_session_even_on_send_error(tmp_path: Path):
    case_dir = _write_case(tmp_path)
    mock_agent = MagicMock()
    mock_agent.agent_id = "agent-xyz"
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)

    with patch(
        "agent.continue_after_approval.resume_agent", return_value=mock_agent
    ):
        with patch(
            "agent.continue_after_approval.send_and_wait",
            side_effect=RuntimeError("fail"),
        ):
            with patch("agent.continue_after_approval.save_session") as mock_save:
                continue_generate_after_approval(case_dir, approver="alice")

    mock_save.assert_called_once_with(case_dir / "outputs", "agent-xyz")
