import json
import sys

import pytest

from agent.tools_runner import run_tools_pipeline
from tests.conftest import require_example_artifacts

pytestmark = pytest.mark.integration


def test_full_tools_pipeline_produces_report(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    out = run_tools_pipeline(example_case_dir, uri=mongo_uri, no_cleanup=True)
    assert out.is_file()
    md = out.with_suffix(".md")
    assert md.is_file()


def test_report_atlas_matches_dbstats_scaling(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    run_tools_pipeline(example_case_dir, uri=mongo_uri, no_cleanup=True)
    report = json.loads(
        (example_case_dir / "outputs" / "sizing-report.json").read_text(encoding="utf-8")
    )
    assert report["atlas"]["diskRequired"] == report["databaseScaling"]["diskRequired"]
    assert report["atlas"]["diskRequired"] > 0
    assert report["atlas"]["ramRequired"] > 0


def test_report_lists_expected_collections(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    run_tools_pipeline(example_case_dir, uri=mongo_uri, no_cleanup=True)
    report = json.loads(
        (example_case_dir / "outputs" / "sizing-report.json").read_text(encoding="utf-8")
    )
    names = {c["name"] for c in report["collections"]}
    assert "client_document_history" in names
    assert "client_release_table" in names


def test_report_coll_storage_reflects_settled_stats(
    example_case_dir, mongo_uri, docker_stack, integration_db_cleanup
):
    require_example_artifacts(example_case_dir)
    run_tools_pipeline(example_case_dir, uri=mongo_uri, no_cleanup=True)
    report = json.loads(
        (example_case_dir / "outputs" / "sizing-report.json").read_text(encoding="utf-8")
    )
    for col in report["collections"]:
        cs = col["collStats"]
        if (cs.get("size") or 0) > 8192:
            assert (cs.get("storageSize") or 0) > 4096, col["name"]
    assert (report["dbStats"].get("storageSize") or 0) > 4096
