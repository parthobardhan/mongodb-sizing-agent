import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: docker mongo required")
    config.addinivalue_line("markers", "agent: cursor api required")


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def example_case_dir(project_root: Path) -> Path:
    return project_root / "cases" / "_example"


@pytest.fixture(scope="session")
def mongo_uri() -> str:
    return os.environ.get("MONGODB_URI", "mongodb://localhost:27017")


@pytest.fixture(scope="session")
def docker_stack(project_root: Path) -> None:
    """Start local MongoDB via docker compose; fail if Docker is unreachable."""
    script = project_root / "scripts" / "run_local_stack.sh"
    subprocess.run(
        ["bash", str(script)],
        cwd=project_root,
        check=True,
    )


def require_example_artifacts(case_dir: Path) -> None:
    """Skip test when committed _example outputs are missing."""
    for rel in (
        "outputs/data-model.md",
        "outputs/sizing_inputs.json",
        "outputs/seed.py",
        "outputs/mongodb_indexes.json",
    ):
        if not (case_dir / rel).is_file():
            pytest.skip(f"missing {rel} in {case_dir}")


@pytest.fixture
def temp_case_dir(example_case_dir: Path, tmp_path: Path) -> Path:
    """Copy _example case to tmp_path for destructive gate tests."""
    dest = tmp_path / "case"
    shutil.copytree(example_case_dir, dest)
    return dest


@pytest.fixture(scope="session", autouse=False)
def integration_db_cleanup(mongo_uri: str, docker_stack: None) -> None:
    """Drop sizing DB after integration module (optional; used via request in tests)."""
    yield
    try:
        from scripts.clear_local_mongo import drop_database

        drop_database(mongo_uri, "sizing_claims_document_history")
    except Exception:
        pass
