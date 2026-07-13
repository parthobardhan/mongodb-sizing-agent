import json
from pathlib import Path

import pytest

from agent.session import (
    PROJECT_ROOT,
    _api_key,
    load_session,
    local_options,
    read_approval_status,
    save_session,
)

EXAMPLE_MODEL = (
    Path(__file__).resolve().parent.parent / "cases/_example/outputs/data-model.md"
)

APPROVED_VARIANTS = [
    "**Approval status:** approved",
    "- Status: **approved**",
]

PENDING_VARIANTS = [
    "**Approval status:** pending",
    "- Status: **pending**",
]


def test_example_data_model_is_approved():
    assert read_approval_status(EXAMPLE_MODEL) == "approved"


def test_read_approval_status_missing(tmp_path: Path):
    assert read_approval_status(tmp_path / "missing.md") == "missing"


@pytest.mark.parametrize("body", APPROVED_VARIANTS)
def test_read_approval_status_approved_variants(tmp_path: Path, body: str):
    path = tmp_path / "data-model.md"
    path.write_text(f"# Model\n\n{body}\n", encoding="utf-8")
    assert read_approval_status(path) == "approved"


@pytest.mark.parametrize("body", PENDING_VARIANTS)
def test_read_approval_status_pending_variants(tmp_path: Path, body: str):
    path = tmp_path / "data-model.md"
    path.write_text(f"# Model\n\n{body}\n", encoding="utf-8")
    assert read_approval_status(path) == "pending"


def test_read_approval_status_unknown_when_word_without_status_line(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(
        "# Model\n\nThis design was approved by the team in review.\n",
        encoding="utf-8",
    )
    assert read_approval_status(path) == "unknown"


def test_pending_header_blocks_despite_approved_footer(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(
        """# Data model

**Approval status:** pending

## 10. Approval
- Status: **approved**
""",
        encoding="utf-8",
    )
    assert read_approval_status(path) == "pending"


def test_approved_header_wins_over_pending_footer(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(
        """# Data model

**Approval status:** approved

## 10. Approval
- Status: **pending**
""",
        encoding="utf-8",
    )
    assert read_approval_status(path) == "approved"


def test_save_and_load_session_roundtrip(tmp_path: Path):
    save_session(tmp_path, "agent-abc", run_id="run-123")
    data = json.loads((tmp_path / "session.json").read_text())
    assert data["agent_id"] == "agent-abc"
    assert data["last_run_id"] == "run-123"
    assert load_session(tmp_path) == "agent-abc"


def test_save_session_without_run_id(tmp_path: Path):
    save_session(tmp_path, "agent-xyz")
    data = json.loads((tmp_path / "session.json").read_text())
    assert data == {"agent_id": "agent-xyz"}
    assert "last_run_id" not in data


def test_load_session_missing_returns_none(tmp_path: Path):
    assert load_session(tmp_path) is None


def test_api_key_raises_when_unset(monkeypatch: pytest.MonkeyPatch):
    from cursor_sdk import CursorAgentError

    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    with pytest.raises(CursorAgentError, match="CURSOR_API_KEY"):
        _api_key()


def test_local_options_uses_project_root():
    opts = local_options()
    assert opts.cwd == str(PROJECT_ROOT)
    assert opts.setting_sources == ["project", "plugins"]
