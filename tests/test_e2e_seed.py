import subprocess
import sys

import pytest
from pymongo import MongoClient

from tests.conftest import require_example_artifacts

pytestmark = pytest.mark.integration

DB_NAME = "sizing_claims_document_history"
COL_HISTORY = "client_document_history"
COL_RELEASE = "client_release_table"
EMBEDDED_AVG_CARDINALITY = 5


def _run_seed(example_case_dir, mongo_uri: str) -> None:
    seed = example_case_dir / "outputs" / "seed.py"
    subprocess.run(
        [sys.executable, str(seed), "--clear", "--uri", mongo_uri],
        check=True,
    )


def test_seed_inserts_500_per_collection(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    _run_seed(example_case_dir, mongo_uri)
    client = MongoClient(mongo_uri)
    db = client[DB_NAME]
    assert db[COL_HISTORY].count_documents({}) == 500
    assert db[COL_RELEASE].count_documents({}) == 500
    client.close()


def test_dbstats_objects_after_seed(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    _run_seed(example_case_dir, mongo_uri)
    client = MongoClient(mongo_uri)
    stats = client[DB_NAME].command("dbStats")
    client.close()
    assert stats["objects"] == 1000


def test_embedded_detail_lines_present(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    _run_seed(example_case_dir, mongo_uri)
    client = MongoClient(mongo_uri)
    doc = client[DB_NAME][COL_HISTORY].find_one()
    client.close()
    assert doc is not None
    lines = doc.get("detailLines", [])
    assert len(lines) >= 1
    client = MongoClient(mongo_uri)
    all_docs = list(client[DB_NAME][COL_HISTORY].find({}, {"detailLines": 1}))
    client.close()
    avg_len = sum(len(d.get("detailLines", [])) for d in all_docs) / len(all_docs)
    assert 2 <= avg_len <= 10
