import os

import pytest

from cursor_sdk import Agent, LocalAgentOptions

pytestmark = pytest.mark.agent


def _api_key_or_skip() -> str:
    key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not key:
        pytest.skip("CURSOR_API_KEY not set")
    return key


@pytest.mark.agent
def test_agent_create_and_short_prompt(project_root):
    api_key = _api_key_or_skip()
    with Agent.create(
        model="composer-2.5",
        api_key=api_key,
        local=LocalAgentOptions(cwd=str(project_root)),
    ) as agent:
        run = agent.send("Reply with exactly: OK")
        result = run.wait()
    assert result.status != "error"
    text = run.text() if hasattr(run, "text") else ""
    if not text:
        for message in run.messages():
            if getattr(message, "type", None) == "assistant":
                msg = getattr(message, "message", message)
                for block in getattr(msg, "content", []):
                    if getattr(block, "type", None) == "text":
                        text += getattr(block, "text", "")
    assert text.strip()


def test_create_agent_helper_succeeds_without_mode_kwarg():
    _api_key_or_skip()
    from agent.session import create_agent
    from unittest.mock import MagicMock, patch

    mock_agent = MagicMock()
    with patch("agent.session.Agent.create", return_value=mock_agent):
        agent = create_agent()
    assert agent is mock_agent
