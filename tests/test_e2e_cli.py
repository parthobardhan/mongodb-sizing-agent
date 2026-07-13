import shutil
import subprocess
import sys
import uuid

import pytest

from tests.conftest import require_example_artifacts

pytestmark = pytest.mark.integration


def test_cli_tools_only_exit_0(
    example_case_dir, mongo_uri, docker_stack, project_root, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "run_agent.py"),
            "--case",
            "_example",
            "--phase",
            "tools-only",
            "--no-cleanup",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_approval_gate_blocks_tools_only(
    example_case_dir, mongo_uri, docker_stack, project_root, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    case_name = f"_pytest_gate_{uuid.uuid4().hex[:8]}"
    case_dir = project_root / "cases" / case_name
    try:
        shutil.copytree(example_case_dir, case_dir)
        data_model = case_dir / "outputs" / "data-model.md"
        text = data_model.read_text(encoding="utf-8")
        data_model.write_text(
            text.replace("approved", "pending").replace("Approved", "Pending"),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(project_root / "run_agent.py"),
                "--case",
                case_name,
                "--phase",
                "tools-only",
                "--no-cleanup",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "MONGODB_URI": mongo_uri},
        )
        assert result.returncode != 0
        assert "approved" in (result.stderr + result.stdout).lower()
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
