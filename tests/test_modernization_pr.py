"""Unit tests for modernization PR notification helpers."""

from __future__ import annotations

from automation.modernization_pr import (
    MODERNIZATION_CASE_LABEL,
    extract_pr_summary,
    format_pr_slack_message,
    has_file_changes,
    is_modernization_pr,
    is_modernization_resource_path,
)

PR_BODY_WITH_MARKERS = """<!-- CURSOR_AGENT_PR_BODY_BEGIN -->
## Summary

Phases 1–3 for **payment-settlement-platform**.

- Anchor: `payment_instruction`
- Approval status: **pending**
<!-- CURSOR_AGENT_PR_BODY_END -->

<div>footer</div>
"""

PR_BODY_PLAIN = """## Summary

Plain summary without markers.

## Artifacts

- cases/foo/outputs/data-model.md
"""


def test_is_modernization_resource_path():
    assert is_modernization_resource_path("cases/payments/outputs/data-model.md")
    assert not is_modernization_resource_path("README.md")
    assert not is_modernization_resource_path("cases/")


def test_is_modernization_pr_by_label():
    assert is_modernization_pr(labels=[MODERNIZATION_CASE_LABEL], changed_files=["README.md"])
    assert is_modernization_pr(labels=[{"name": MODERNIZATION_CASE_LABEL}], changed_files=[])


def test_is_modernization_pr_by_cases_path():
    assert is_modernization_pr(
        changed_files=[{"path": "cases/payments/outputs/data-model.md"}],
    )
    assert not is_modernization_pr(changed_files=[".gitignore", "README.md"])


def test_is_modernization_pr_by_title():
    assert is_modernization_pr(
        title="Modernization resources: payment-settlement",
        changed_files=[],
    )
    assert not is_modernization_pr(title="Fix typo in README", changed_files=[])


def test_is_modernization_pr_rejects_unrelated():
    assert not is_modernization_pr(
        labels=["bug"],
        changed_files=["dashboard/server.py"],
        title="Dashboard tweak",
    )


def test_has_file_changes():
    assert has_file_changes([{"path": "README.md"}])
    assert not has_file_changes([])


def test_extract_pr_summary_from_markers():
    summary = extract_pr_summary(PR_BODY_WITH_MARKERS)
    assert "payment-settlement-platform" in summary
    assert "CURSOR_AGENT" not in summary
    assert "<div>" not in summary


def test_extract_pr_summary_from_summary_section():
    summary = extract_pr_summary(PR_BODY_PLAIN)
    assert summary.startswith("Plain summary without markers.")


def test_extract_pr_summary_empty():
    assert extract_pr_summary(None) == "_No PR summary provided._"
    assert extract_pr_summary("   ") == "_No PR summary provided._"


def test_format_pr_slack_message():
    message = format_pr_slack_message(
        pr_number=30,
        title="Modernization resources: payment-settlement",
        summary="## Summary\n\nPending approval.",
        pr_url="https://github.com/org/repo/pull/30",
        author="test-user",
    )
    assert "PR #30" in message
    assert "https://github.com/org/repo/pull/30" in message
    assert "Approve" in message
    assert "Suggest changes" in message
    assert "test-user" in message
