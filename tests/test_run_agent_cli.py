import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import run_agent


def test_main_unknown_case_exits_1():
    assert run_agent.main(["--case", "nonexistent_case_xyz"]) == 1


def test_main_invalid_intake_exits_or_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    case_dir = tmp_path / "bad_case"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(json.dumps({"queryLatencySlaMs": 50}), encoding="utf-8")

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    with pytest.raises(Exception):
        run_agent.main(["--case", "bad_case"])


def test_tools_only_calls_run_tools_pipeline(
    example_case_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: example_case_dir)
    with patch.object(run_agent, "run_tools_pipeline") as mock_pipeline:
        with patch.object(run_agent, "create_agent") as mock_create:
            code = run_agent.main(
                ["--case", "_example", "--phase", "tools-only", "--no-cleanup"]
            )
    assert code == 0
    mock_pipeline.assert_called_once()
    mock_create.assert_not_called()


def test_interactive_calls_create_agent_when_no_session(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "agent-new"

    try:
        with patch.object(run_agent, "create_agent", return_value=mock_agent) as mock_create:
            with patch.object(run_agent, "resume_agent") as mock_resume:
                with patch.object(run_agent, "send_and_wait"):
                    with patch.object(run_agent, "load_session", return_value=None):
                        with patch("builtins.input", return_value="quit"):
                            code = run_agent.main(["--case", case_name])

        assert code == 0
        mock_create.assert_called_once()
        mock_resume.assert_not_called()
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_interactive_resumes_when_session_exists(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )
    (outputs / "session.json").write_text(
        json.dumps({"agent_id": "existing-agent"}), encoding="utf-8"
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "existing-agent"

    try:
        with patch.object(run_agent, "create_agent") as mock_create:
            with patch.object(run_agent, "resume_agent", return_value=mock_agent) as mock_resume:
                with patch.object(run_agent, "send_and_wait"):
                    with patch("builtins.input", return_value="quit"):
                        code = run_agent.main(["--case", case_name])

        assert code == 0
        mock_resume.assert_called_once_with("existing-agent")
        mock_create.assert_not_called()
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_interactive_sends_plan_mode_until_approve(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "agent-new"

    try:
        with patch.object(run_agent, "create_agent", return_value=mock_agent):
            with patch.object(run_agent, "resume_agent") as mock_resume:
                with patch.object(run_agent, "send_and_wait") as mock_send:
                    with patch.object(run_agent, "load_session", return_value=None):
                        with patch(
                            "builtins.input",
                            side_effect=["tweak the model", "approve", "quit"],
                        ):
                            code = run_agent.main(["--case", case_name])

        assert code == 0
        mock_resume.assert_not_called()
        assert mock_send.call_args_list == [
            call(mock_agent, run_agent.SYSTEM_PROMPT, mode="plan"),
            call(
                mock_agent,
                run_agent.initial_case_message(case_dir, case_name),
                mode="plan",
            ),
            call(mock_agent, "tweak the model", mode="plan"),
            call(mock_agent, "approve", mode="agent"),
        ]
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_interactive_resumes_in_agent_mode_when_already_approved(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )
    (outputs / "session.json").write_text(
        json.dumps({"agent_id": "existing-agent"}), encoding="utf-8"
    )
    (outputs / "data-model.md").write_text(
        "**Approval status:** approved\n", encoding="utf-8"
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "existing-agent"

    try:
        with patch.object(run_agent, "create_agent") as mock_create:
            with patch.object(run_agent, "resume_agent", return_value=mock_agent):
                with patch.object(run_agent, "send_and_wait") as mock_send:
                    with patch(
                        "builtins.input",
                        side_effect=["regenerate seed", "quit"],
                    ):
                        code = run_agent.main(["--case", case_name])

        assert code == 0
        mock_create.assert_not_called()
        mock_send.assert_called_once_with(
            mock_agent, "regenerate seed", mode="agent"
        )
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_interactive_approve_skips_tools_when_artifacts_missing(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )
    (outputs / "session.json").write_text(
        json.dumps({"agent_id": "existing-agent"}), encoding="utf-8"
    )
    (outputs / "data-model.md").write_text(
        "**Approval status:** approved\n", encoding="utf-8"
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "existing-agent"

    try:
        with patch.object(run_agent, "create_agent"):
            with patch.object(run_agent, "resume_agent", return_value=mock_agent):
                with patch.object(run_agent, "send_and_wait"):
                    with patch.object(run_agent, "run_tools_pipeline") as mock_pipeline:
                        with patch(
                            "builtins.input",
                            side_effect=["approve", "quit"],
                        ):
                            code = run_agent.main(["--case", case_name])

        assert code == 0
        mock_pipeline.assert_not_called()
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_interactive_saves_session_before_bootstrap(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    from cursor_sdk import CursorAgentError

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "agent-early"

    try:
        with patch.object(run_agent, "create_agent", return_value=mock_agent):
            with patch.object(run_agent, "load_session", return_value=None):
                with patch.object(run_agent, "save_session") as mock_save:
                    with patch.object(
                        run_agent,
                        "send_and_wait",
                        side_effect=CursorAgentError("bootstrap failed"),
                    ):
                        code = run_agent.main(["--case", case_name])

        assert code == 1
        assert mock_save.call_args_list[0] == call(outputs, "agent-early")
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_interactive_continues_after_send_error(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
):
    import shutil
    import uuid

    from cursor_sdk import CursorAgentError

    case_name = f"_pytest_cli_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    outputs = case_dir / "outputs"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text(
        json.dumps(
            {
                "useCaseName": "demo-case",
                "queryLatencySlaMs": 50,
                "assumptions": [],
            }
        ),
        encoding="utf-8",
    )
    (outputs / "session.json").write_text(
        json.dumps({"agent_id": "existing-agent"}), encoding="utf-8"
    )

    monkeypatch.setattr(run_agent, "case_dir_for", lambda name: case_dir)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=False)
    mock_agent.agent_id = "existing-agent"

    try:
        with patch.object(run_agent, "create_agent"):
            with patch.object(run_agent, "resume_agent", return_value=mock_agent):
                with patch.object(
                    run_agent,
                    "send_and_wait",
                    side_effect=[CursorAgentError("transient"), MagicMock()],
                ) as mock_send:
                    with patch(
                        "builtins.input",
                        side_effect=["first", "second", "quit"],
                    ):
                        code = run_agent.main(["--case", case_name])

        assert code == 0
        assert mock_send.call_count == 2
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
