from pathlib import Path

import pytest

from agent.tools_runner import (
    missing_tools_artifacts,
    verify_approved,
    verify_tools_ready,
)

APPROVED_MD = "# Model\n\n**Approval status:** approved\n"
PENDING_MD = "# Model\n\n**Approval status:** pending\n"


def test_verify_approved_passes_on_approved(tmp_path: Path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "data-model.md").write_text(APPROVED_MD, encoding="utf-8")
    verify_approved(tmp_path)


def test_verify_approved_raises_on_pending(tmp_path: Path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "data-model.md").write_text(PENDING_MD, encoding="utf-8")
    with pytest.raises(RuntimeError, match="pending"):
        verify_approved(tmp_path)


def test_verify_approved_raises_on_missing(tmp_path: Path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    with pytest.raises(RuntimeError, match="missing"):
        verify_approved(tmp_path)


def test_missing_tools_artifacts_lists_absent_files(tmp_path: Path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "seed.py").write_text("# seed\n", encoding="utf-8")
    missing = missing_tools_artifacts(tmp_path)
    assert [p.name for p in missing] == [
        "mongodb_indexes.json",
        "sizing_inputs.json",
    ]


def test_verify_tools_ready_requires_generate_artifacts(tmp_path: Path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "data-model.md").write_text(APPROVED_MD, encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Generate-phase artifacts"):
        verify_tools_ready(tmp_path)


def test_verify_tools_ready_passes_when_approved_and_complete(tmp_path: Path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "data-model.md").write_text(APPROVED_MD, encoding="utf-8")
    (outputs / "seed.py").write_text("# seed\n", encoding="utf-8")
    (outputs / "mongodb_indexes.json").write_text("{}", encoding="utf-8")
    (outputs / "sizing_inputs.json").write_text("{}", encoding="utf-8")
    verify_tools_ready(tmp_path)
