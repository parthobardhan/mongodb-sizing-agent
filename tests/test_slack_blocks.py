"""Unit tests for Slack Block Kit builders."""

from __future__ import annotations

import json
from pathlib import Path

from slack_app.blocks import (
    ACTION_APPROVE,
    ACTION_REQUEST_CHANGES,
    build_approval_request_blocks,
    build_sizing_summary_blocks,
    extract_disposition_summary,
    format_bytes,
    parse_case_action_value,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CASE = PROJECT_ROOT / "cases" / "_example"
EXAMPLE_MODEL = EXAMPLE_CASE / "outputs" / "data-model.md"
EXAMPLE_REPORT = EXAMPLE_CASE / "outputs" / "sizing-report.json"


def test_format_bytes_gb():
    assert "GB" in format_bytes(2512213333)


def test_extract_disposition_summary_from_example():
    text = EXAMPLE_MODEL.read_text(encoding="utf-8")
    lines = extract_disposition_summary(text)
    assert len(lines) >= 2
    assert any("CLIENT_DOCUMENT_HISTORY" in line for line in lines)
    assert any("embedded" in line for line in lines)


def test_build_approval_request_blocks_has_buttons():
    blocks = build_approval_request_blocks(
        case_name="_example",
        use_case_display="claims-document-history",
        disposition_lines=["• `foo` → anchor → `bar`"],
        sla_ms=50,
    )
    actions = [b for b in blocks if b.get("type") == "actions"]
    assert len(actions) == 1
    elements = actions[0]["elements"]
    action_ids = {e["action_id"] for e in elements}
    assert ACTION_APPROVE in action_ids
    assert ACTION_REQUEST_CHANGES in action_ids
    assert parse_case_action_value(elements[0]["value"]) == "_example"


def test_build_sizing_summary_from_example_report():
    report = json.loads(EXAMPLE_REPORT.read_text(encoding="utf-8"))
    blocks = build_sizing_summary_blocks(
        case_name="_example",
        report=report,
        report_path="cases/_example/outputs/sizing-report.json",
    )
    assert blocks[0]["type"] == "header"
    fields = blocks[1]["fields"]
    disk_field = next(f for f in fields if "disk" in f["text"].lower())
    assert "GB" in disk_field["text"]


def test_build_sizing_summary_handles_missing_atlas():
    blocks = build_sizing_summary_blocks(case_name="x", report={})
    assert blocks[0]["type"] == "header"
