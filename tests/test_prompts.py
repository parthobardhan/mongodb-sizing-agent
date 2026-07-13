import shutil
import uuid
from pathlib import Path

import pytest

from agent.prompts import PROJECT_ROOT, SYSTEM_PROMPT, initial_case_message


@pytest.fixture
def case_under_project(project_root: Path):
    """Transient case directory under cases/ (required by initial_case_message)."""
    name = f"_pytest_prompt_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / name
    case_dir.mkdir(parents=True)
    yield case_dir
    shutil.rmtree(case_dir, ignore_errors=True)


def test_initial_case_message_lists_existing_files_only(case_under_project: Path):
    inputs = case_under_project / "inputs"
    inputs.mkdir()
    (inputs / "intake.json").write_text("{}", encoding="utf-8")
    (inputs / "schema.sql").write_text("-- ddl", encoding="utf-8")

    msg = initial_case_message(case_under_project, "my-case")

    assert "intake.json" in msg
    assert "schema.sql" in msg
    assert "indexes.sql" not in msg
    assert "sizing_inputs.json" not in msg


def test_initial_case_message_includes_use_case_and_relative_paths(example_case_dir: Path):
    rel_case = example_case_dir.relative_to(PROJECT_ROOT)
    msg = initial_case_message(example_case_dir, "claims-document-history")

    assert "Use case: claims-document-history" in msg
    assert f"Case directory: {rel_case}" in msg
    assert "intake.json" in msg
    assert "Begin intake and document modeling" in msg


def test_system_prompt_mentions_key_artifacts():
    assert "data-model.md" in SYSTEM_PROMPT
    assert "outputs/sizing_inputs.json" in SYSTEM_PROMPT
    assert "seed.py" in SYSTEM_PROMPT
    assert "size_from_dbstats.py" in SYSTEM_PROMPT
