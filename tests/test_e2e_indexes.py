import json
import subprocess
import sys

import pytest
from pymongo import MongoClient

from scripts.index_utils import assert_no_redundant_prefix_indexes
from tests.conftest import require_example_artifacts

pytestmark = pytest.mark.integration

DB_NAME = "sizing_claims_document_history"


def _seed(example_case_dir, mongo_uri: str) -> None:
    seed = example_case_dir / "outputs" / "seed.py"
    subprocess.run(
        [sys.executable, str(seed), "--clear", "--uri", mongo_uri],
        check=True,
    )


def test_apply_indexes_creates_expected_names(
    example_case_dir, mongo_uri, docker_stack, project_root, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    _seed(example_case_dir, mongo_uri)
    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "apply_indexes.py"),
            "--uri",
            mongo_uri,
            "--case",
            str(example_case_dir),
        ],
        check=True,
        cwd=project_root,
    )
    client = MongoClient(mongo_uri)
    history_indexes = client[DB_NAME]["client_document_history"].index_information()
    release_indexes = client[DB_NAME]["client_release_table"].index_information()
    client.close()
    history_names = set(history_indexes.keys())
    release_names = set(release_indexes.keys())
    assert "cKey_1" in history_names
    assert "cKey_cKey_Type_cCopy_Number" in release_names


def test_example_spec_has_no_redundant_prefixes(example_case_dir):
    require_example_artifacts(example_case_dir)
    spec_path = example_case_dir / "outputs" / "mongodb_indexes.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert_no_redundant_prefix_indexes(spec)
