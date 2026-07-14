import subprocess
import sys

import pytest

from agent.tools_runner import run_tools_pipeline
from tests.conftest import require_example_artifacts

pytestmark = pytest.mark.integration


def test_repository_methods_against_seeded_data(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    repo_test = example_case_dir / "outputs" / "test_mongo_repository.py"
    if not repo_test.is_file():
        pytest.skip("missing outputs/test_mongo_repository.py")

    run_tools_pipeline(example_case_dir, uri=mongo_uri, no_cleanup=True)


def test_repository_tests_run_standalone(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    repo_test = example_case_dir / "outputs" / "test_mongo_repository.py"
    seed = example_case_dir / "outputs" / "seed.py"
    if not repo_test.is_file():
        pytest.skip("missing outputs/test_mongo_repository.py")

    subprocess.run([sys.executable, str(seed), "--clear", "--uri", mongo_uri], check=True)
    env = {"MONGODB_URI": mongo_uri, **dict(__import__("os").environ)}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(repo_test), "-v"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
