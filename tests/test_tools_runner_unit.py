from pathlib import Path
from unittest.mock import patch

import pytest

from agent.tools_runner import (
    missing_tools_artifacts,
    run_tools_pipeline,
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


def _minimal_case(tmp_path: Path) -> Path:
    """Case dir with inputs and approved generate-phase outputs."""
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "intake.json").write_text(
        '{"useCaseName": "claims-document-history", "queryLatencySlaMs": 50}',
        encoding="utf-8",
    )
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "data-model.md").write_text(APPROVED_MD, encoding="utf-8")
    (outputs / "seed.py").write_text("# seed\n", encoding="utf-8")
    (outputs / "mongodb_indexes.json").write_text("{}", encoding="utf-8")
    (outputs / "sizing_inputs.json").write_text(
        '{"collections": [], "embedded": {}, "databaseProductionDocumentCount": 1000}',
        encoding="utf-8",
    )
    return tmp_path


@patch("agent.tools_runner.run")
def test_run_tools_pipeline_skips_repo_tests_when_absent(mock_run, tmp_path: Path):
    case_dir = _minimal_case(tmp_path)
    (case_dir / "outputs" / "sizing-report.json").write_text("{}", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        if "size_from_dbstats.py" in cmd:
            out = case_dir / "outputs" / "sizing-report.json"
            out.write_text("{}", encoding="utf-8")
        from subprocess import CompletedProcess

        return CompletedProcess(cmd, 0)

    mock_run.side_effect = fake_run

    with patch("agent.tools_runner.load_sizing_inputs") as mock_load:
        mock_load.return_value = {"databaseProductionDocumentCount": 1000}
        with patch("agent.tools_runner.database_production_document_count", return_value=1000):
            run_tools_pipeline(case_dir, no_cleanup=True)

    pytest_calls = [c for c in mock_run.call_args_list if "pytest" in c.args[0]]
    assert pytest_calls == []


@patch("agent.tools_runner.run")
def test_run_tools_pipeline_runs_repo_tests_when_present(mock_run, tmp_path: Path):
    case_dir = _minimal_case(tmp_path)
    repo_test = case_dir / "outputs" / "test_mongo_repository.py"
    repo_test.write_text("def test_ok(): pass\n", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        if "size_from_dbstats.py" in cmd:
            out = case_dir / "outputs" / "sizing-report.json"
            out.write_text("{}", encoding="utf-8")
        from subprocess import CompletedProcess

        return CompletedProcess(cmd, 0)

    mock_run.side_effect = fake_run

    with patch("agent.tools_runner.load_sizing_inputs") as mock_load:
        mock_load.return_value = {"databaseProductionDocumentCount": 1000}
        with patch("agent.tools_runner.database_production_document_count", return_value=1000):
            run_tools_pipeline(case_dir, no_cleanup=True)

    pytest_calls = [c for c in mock_run.call_args_list if "pytest" in c.args[0]]
    assert len(pytest_calls) == 1
    assert str(repo_test) in pytest_calls[0].args[0]
