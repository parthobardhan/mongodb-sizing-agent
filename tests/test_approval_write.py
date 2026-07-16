"""Unit tests for approve_data_model file writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.approval import approve_data_model
from agent.session import read_approval_status

PENDING_HEADER = """# Data model: test-case

**Approval status:** pending

## 2. Relational table disposition

| Relational table | Disposition | MongoDB target |
|------------------|-------------|----------------|
| FOO | anchor | `foo` |

## 10. Approval

- Status: **pending**
"""

PENDING_FOOTER_ONLY = """# Data model: test-case

**Approval status:** pending

## 10. Approval

- Status: **pending**
"""


def test_approve_flips_header_and_footer(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(PENDING_HEADER, encoding="utf-8")
    status = approve_data_model(path, "demo-user")
    assert status == "approved"
    text = path.read_text(encoding="utf-8")
    assert "**Approval status:** approved" in text
    assert "- Status: **approved**" in text
    assert "- Approved by: demo-user" in text
    assert "- Via: Slack" in text
    assert read_approval_status(path) == "approved"


def test_approve_idempotent_when_already_approved(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(
        "# Test\n\n**Approval status:** approved\n\n## 10. Approval\n\n- Status: **approved**\n",
        encoding="utf-8",
    )
    status = approve_data_model(path, "someone")
    assert status == "approved"
    assert path.read_text(encoding="utf-8").count("Approved by:") == 0


def test_approve_raises_without_status_line(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text("# No approval block\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no approval status"):
        approve_data_model(path, "user")


def test_approve_appends_section_when_missing_footer(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(
        "# Test\n\n**Approval status:** pending\n",
        encoding="utf-8",
    )
    approve_data_model(path, "alice")
    text = path.read_text(encoding="utf-8")
    assert "## 10. Approval" in text
    assert "- Approved by: alice" in text


def test_approve_preserves_body_content(tmp_path: Path):
    path = tmp_path / "data-model.md"
    path.write_text(PENDING_FOOTER_ONLY, encoding="utf-8")
    approve_data_model(path, "bob")
    text = path.read_text(encoding="utf-8")
    assert "test-case" in text
    assert read_approval_status(path) == "approved"
