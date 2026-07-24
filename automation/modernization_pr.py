"""Detect modernization PRs and format Slack notifications for review."""

from __future__ import annotations

import re
from typing import Iterable

MODERNIZATION_CASE_LABEL = "modernization-case"
MODERNIZATION_TITLE_PREFIX = "Modernization resources:"
MODERNIZATION_PATH_PREFIX = "cases/"

_CURSOR_AGENT_BODY_RE = re.compile(
    r"<!--\s*CURSOR_AGENT_PR_BODY_BEGIN\s*-->\s*(.*?)\s*<!--\s*CURSOR_AGENT_PR_BODY_END\s*-->",
    re.DOTALL | re.IGNORECASE,
)
_SUMMARY_SECTION_RE = re.compile(
    r"^##\s+Summary\s*\n+(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _normalize_labels(labels: Iterable[str | dict[str, str]]) -> set[str]:
    names: set[str] = set()
    for label in labels:
        if isinstance(label, str):
            names.add(label)
        elif isinstance(label, dict):
            name = label.get("name")
            if name:
                names.add(name)
    return names


def _normalize_paths(changed_files: Iterable[str | dict[str, str]]) -> list[str]:
    paths: list[str] = []
    for item in changed_files:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict):
            path = item.get("path") or item.get("filename")
            if path:
                paths.append(path)
    return paths


def is_modernization_resource_path(path: str) -> bool:
    """Return True when a changed file is under cases/ (modernization workload)."""
    normalized = path.lstrip("./")
    return normalized.startswith(MODERNIZATION_PATH_PREFIX) and normalized != MODERNIZATION_PATH_PREFIX


def is_modernization_pr(
    *,
    labels: Iterable[str | dict[str, str]] | None = None,
    changed_files: Iterable[str | dict[str, str]] | None = None,
    title: str | None = None,
) -> bool:
    """
    Return True when a PR should trigger modernization review notifications.

    Triggers when the PR has the modernization-case label, changes modernization
    resources under cases/, or uses the Modernization resources title prefix.
    """
    label_names = _normalize_labels(labels or ())
    if MODERNIZATION_CASE_LABEL in label_names:
        return True

    paths = _normalize_paths(changed_files or ())
    if any(is_modernization_resource_path(path) for path in paths):
        return True

    if title and title.strip().startswith(MODERNIZATION_TITLE_PREFIX):
        return True

    return False


def has_file_changes(changed_files: Iterable[str | dict[str, str]] | None) -> bool:
    """Return True when the PR includes at least one changed file."""
    return bool(_normalize_paths(changed_files or ()))


def extract_pr_summary(body: str | None) -> str:
    """Extract the human-readable summary from a GitHub PR body."""
    if not body or not body.strip():
        return "_No PR summary provided._"

    match = _CURSOR_AGENT_BODY_RE.search(body)
    if match:
        summary = match.group(1).strip()
        if summary:
            return summary

    match = _SUMMARY_SECTION_RE.search(body)
    if match:
        summary = match.group(1).strip()
        if summary:
            return summary

    stripped = body.strip()
    if len(stripped) > 3000:
        return stripped[:3000].rstrip() + "\n\n_…summary truncated_"
    return stripped


def format_pr_slack_message(
    *,
    pr_number: int | str,
    title: str,
    summary: str,
    pr_url: str,
    author: str | None = None,
) -> str:
    """Format the Slack message for a modernization PR review request."""
    author_line = f"\n*Author:* {author}" if author else ""
    return (
        f":github: *Modernization PR ready for review*\n\n"
        f"*<{pr_url}|PR #{pr_number}: {title}>*{author_line}\n\n"
        f"{summary}\n\n"
        f"Please review the PR on GitHub and *Approve* or *Suggest changes*."
    )
