import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.session import (
    DEFAULT_MODEL,
    _recover_stuck_runs,
    _send_options,
    _wait_run,
    create_agent,
    initial_send_mode,
    resume_agent,
    send_and_wait,
    stream_run_text,
)
from concurrent.futures import TimeoutError as FuturesTimeoutError
from cursor_sdk import Agent, AgentOptions, CursorAgentError, SendOptions


def test_create_agent_calls_agent_create_with_current_kwargs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test_key")
    mock_agent = MagicMock()
    with patch.object(Agent, "create", return_value=mock_agent) as mock_create:
        result = create_agent()
    assert result is mock_agent
    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs["model"] == DEFAULT_MODEL
    assert kwargs["api_key"] == "cursor_test_key"
    assert "mode" not in kwargs
    assert kwargs["local"].cwd is not None
    assert kwargs["local"].setting_sources == ["project", "plugins"]


def test_create_agent_sdk_accepts_kwargs_without_mode(monkeypatch: pytest.MonkeyPatch):
    """Agent.create accepts model/api_key/local without mode kwarg."""
    monkeypatch.setenv("CURSOR_API_KEY", os.environ.get("CURSOR_API_KEY", "cursor_test_key"))
    from agent.session import local_options

    import inspect
    sig = inspect.signature(Agent.create)
    assert "mode" not in sig.parameters
    # Do not call live Agent.create without bridge; signature check is sufficient.


def test_send_options_includes_model_for_plan_mode():
    opts = _send_options("plan")
    assert opts is not None
    assert opts.mode == "plan"
    assert opts.model == DEFAULT_MODEL


def test_send_options_none_without_mode():
    assert _send_options(None) is None


def test_resume_agent_passes_agent_options(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test_key")
    mock_agent = MagicMock()
    with patch.object(Agent, "resume", return_value=mock_agent) as mock_resume:
        result = resume_agent("agent-123")
    assert result is mock_agent
    mock_resume.assert_called_once()
    agent_id, options = mock_resume.call_args.args
    assert agent_id == "agent-123"
    assert isinstance(options, AgentOptions)
    assert options.api_key == "cursor_test_key"
    assert options.model == DEFAULT_MODEL
    assert options.local.setting_sources == ["project", "plugins"]


def test_send_and_wait_without_mode():
    agent = MagicMock()
    agent.agent_id = "a1"
    run = MagicMock()
    run.id = "run-1"
    run.wait.return_value = MagicMock(status="finished")
    run.messages.return_value = []
    agent.send.return_value = run

    result = send_and_wait(agent, "hello")

    agent.send.assert_called_once_with("hello")
    assert result.status == "finished"


def test_send_and_wait_with_mode():
    agent = MagicMock()
    agent.agent_id = "a1"
    run = MagicMock()
    run.id = "run-1"
    run.wait.return_value = MagicMock(status="finished")
    run.messages.return_value = []
    agent.send.return_value = run

    send_and_wait(agent, "approve", mode="agent")

    agent.send.assert_called_once()
    args, kwargs = agent.send.call_args
    assert args[0] == "approve"
    assert isinstance(args[1], SendOptions)
    assert args[1].mode == "agent"
    assert args[1].model == DEFAULT_MODEL


def test_send_and_wait_raises_on_error_status():
    agent = MagicMock()
    agent.agent_id = "a1"
    run = MagicMock()
    run.id = "run-1"
    run.wait.return_value = MagicMock(status="error")
    run.messages.return_value = []
    agent.send.return_value = run

    with pytest.raises(CursorAgentError, match="Agent run failed"):
        send_and_wait(agent, "hello")


def test_stream_run_text_concatenates_assistant_blocks():
    from types import SimpleNamespace

    # Use SimpleNamespace so MagicMock auto-attrs (name/path) do not look like tools.
    block1 = SimpleNamespace(type="text", text="Hello ")
    block2 = SimpleNamespace(type="text", text="world")
    msg = SimpleNamespace(content=[block1, block2])
    assistant = SimpleNamespace(type="assistant", message=msg)
    other = SimpleNamespace(type="user", message=SimpleNamespace(content=[]))

    run = MagicMock()
    run.id = "run-abc"
    run.messages.return_value = [other, assistant]

    with patch("builtins.print"):
        with patch("agent.session.emit_event") as mock_emit:
            text = stream_run_text(run)

    assert text == "Hello world"
    mock_emit.assert_called_once_with(
        "assistant_text", text="Hello world", run_id="run-abc"
    )


def test_stream_run_text_flushes_before_tool_activity():
    from types import SimpleNamespace

    # Use SimpleNamespace so MagicMock auto-attrs (name/path) do not look like tools.
    block = SimpleNamespace(type="text", text="Planning…")
    assistant = SimpleNamespace(
        type="assistant",
        message=SimpleNamespace(content=[block]),
    )
    tool_msg = SimpleNamespace(
        type="tool_call",
        name="Write",
        path="cases/_example/outputs/data-model.md",
        args={},
    )
    run = MagicMock()
    run.id = "run-xyz"
    run.messages.return_value = [assistant, tool_msg]

    with patch("builtins.print"):
        with patch("agent.session.emit_event") as mock_emit:
            text = stream_run_text(run)

    assert text == "Planning…"
    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list[0].args[0] == "assistant_text"
    assert mock_emit.call_args_list[0].kwargs == {
        "text": "Planning…",
        "run_id": "run-xyz",
    }
    assert mock_emit.call_args_list[1].args[0] == "tool_activity"
    assert mock_emit.call_args_list[1].kwargs["tool"] == "Write"
    assert (
        mock_emit.call_args_list[1].kwargs["target"]
        == "cases/_example/outputs/data-model.md"
    )


def test_stream_run_text_prints_tool_activity():
    from types import SimpleNamespace

    tool_msg = SimpleNamespace(
        type="tool_call",
        name="Write",
        path="cases/_example/outputs/data-model.md",
        args={},
    )
    run = MagicMock()
    run.messages.return_value = [tool_msg]

    with patch("builtins.print") as mock_print:
        text = stream_run_text(run)

    assert text == ""
    printed = " ".join(
        str(c.args[0]) for c in mock_print.call_args_list if c.args
    )
    assert "[tool: Write cases/_example/outputs/data-model.md]" in printed


def test_recover_stuck_runs_cancels_supported_running_runs(monkeypatch: pytest.MonkeyPatch):
    running = MagicMock(status="running", id="run-1")
    finished = MagicMock(status="finished", id="run-2")
    mock_run = MagicMock()
    mock_run.supports.return_value = True

    with patch.object(Agent, "list_runs", return_value=[running, finished]):
        with patch.object(Agent, "get_run", return_value=mock_run):
            recovered = _recover_stuck_runs("agent-123")

    assert recovered == ["run-1"]
    mock_run.cancel.assert_called_once()
    mock_run.wait.assert_called_once()


def test_recover_stuck_runs_skips_when_cancel_not_supported():
    running = MagicMock(status="running", id="run-1")
    mock_run = MagicMock()
    mock_run.supports.return_value = False

    with patch.object(Agent, "list_runs", return_value=[running]):
        with patch.object(Agent, "get_run", return_value=mock_run):
            recovered = _recover_stuck_runs("agent-123")

    assert recovered == []
    mock_run.cancel.assert_not_called()
    mock_run.wait.assert_not_called()


def test_recover_stuck_runs_returns_empty_when_list_runs_fails():
    with patch.object(Agent, "list_runs", side_effect=CursorAgentError("boom")):
        assert _recover_stuck_runs("agent-123") == []


def test_recover_stuck_runs_skips_when_wait_times_out():
    running = MagicMock(status="running", id="run-1")
    mock_run = MagicMock()
    mock_run.supports.return_value = True

    with patch.object(Agent, "list_runs", return_value=[running]):
        with patch.object(Agent, "get_run", return_value=mock_run):
            with patch(
                "agent.session._wait_run",
                side_effect=TimeoutError("run.wait() timed out after 0.05s"),
            ):
                recovered = _recover_stuck_runs("agent-123")

    assert recovered == []
    mock_run.cancel.assert_called_once()


def test_wait_run_raises_timeout_and_shuts_down_without_waiting():
    run = MagicMock()
    with patch("agent.session.ThreadPoolExecutor") as mock_pool_cls:
        mock_executor = MagicMock()
        mock_pool_cls.return_value = mock_executor
        mock_future = MagicMock()
        mock_executor.submit.return_value = mock_future
        mock_future.result.side_effect = FuturesTimeoutError()

        with pytest.raises(TimeoutError, match="timed out after 1.0s"):
            _wait_run(run, timeout_sec=1.0)

    mock_executor.submit.assert_called_once_with(run.wait)
    mock_future.result.assert_called_once_with(timeout=1.0)
    mock_executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


def test_initial_send_mode_plan_when_not_approved(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text("**Approval status:** pending\n", encoding="utf-8")
    assert initial_send_mode(path) == "plan"


def test_initial_send_mode_agent_when_approved(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text("**Approval status:** approved\n", encoding="utf-8")
    assert initial_send_mode(path) == "agent"
