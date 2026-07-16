"""Slack Block Kit builders for sizing agent approval and reports."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ACTION_APPROVE = "approve_data_model"
ACTION_REQUEST_CHANGES = "request_changes"

_DISPOSITION_ROW_RE = re.compile(
    r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|$"
)


def format_bytes(value: float | int | None) -> str:
    if value is None:
        return "—"
    n = float(value)
    gb = n / (1024**3)
    if gb >= 1:
        return f"{gb:.2f} GB"
    mb = n / (1024**2)
    return f"{mb:.1f} MB"


def extract_disposition_summary(data_model_text: str) -> list[str]:
    """Return human-readable disposition lines from the disposition table."""
    lines: list[str] = []
    in_table = False
    for raw in data_model_text.splitlines():
        if "Relational table disposition" in raw:
            in_table = True
            continue
        if in_table and raw.startswith("## "):
            break
        if not in_table:
            continue
        if raw.strip().startswith("|--"):
            continue
        if raw.strip().startswith("| Relational"):
            continue
        match = _DISPOSITION_ROW_RE.match(raw.strip())
        if not match:
            continue
        table, disposition, target = (c.strip() for c in match.groups())
        lines.append(f"• `{table}` → {disposition} → {target}")
    return lines


def case_action_value(case_name: str) -> str:
    return json.dumps({"case": case_name})


def parse_case_action_value(value: str | None) -> str | None:
    if not value:
        return None
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value
    return data.get("case")


def build_approval_request_blocks(
    *,
    case_name: str,
    use_case_display: str,
    disposition_lines: list[str],
    sla_ms: int | None,
) -> list[dict[str, Any]]:
    summary = "\n".join(disposition_lines[:6]) if disposition_lines else "_No disposition table found._"
    if len(disposition_lines) > 6:
        summary += f"\n_…and {len(disposition_lines) - 6} more_"

    sla_line = f"Query latency SLA: *{sla_ms} ms*" if sla_ms else "Query latency SLA: _not specified_"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Data model ready: {use_case_display}", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Case:* `{case_name}`\n"
                    f"{sla_line}\n"
                    f"*Approval status:* `pending`\n\n"
                    f"*Disposition*\n{summary}"
                ),
            },
        },
        {
            "type": "actions",
            "block_id": f"approval_actions_{case_name}",
            "elements": [
                {
                    "type": "button",
                    "action_id": ACTION_APPROVE,
                    "text": {"type": "plain_text", "text": "Approve", "emoji": True},
                    "style": "primary",
                    "value": case_action_value(case_name),
                },
                {
                    "type": "button",
                    "action_id": ACTION_REQUEST_CHANGES,
                    "text": {"type": "plain_text", "text": "Request changes", "emoji": True},
                    "value": case_action_value(case_name),
                },
            ],
        },
    ]


def build_approved_message_blocks(*, approver: str, approved_at: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":white_check_mark: *Approved* by {approver}\n_{approved_at}_",
            },
        }
    ]


def build_request_changes_blocks(*, requester: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":speech_balloon: *Changes requested* by {requester}\nReply in thread with feedback.",
            },
        }
    ]


def build_sizing_summary_blocks(
    *,
    case_name: str,
    report: dict[str, Any],
    report_path: str | None = None,
) -> list[dict[str, Any]]:
    atlas = report.get("atlas") or {}
    db_scaling = report.get("databaseScaling") or {}
    prod_count = report.get("databaseProductionDocumentCount")
    compression = db_scaling.get("compression")

    disk = format_bytes(atlas.get("diskRequired"))
    ram = format_bytes(atlas.get("ramRequired"))
    compression_pct = f"{compression * 100:.1f}%" if compression is not None else "—"

    path_line = f"\nReport: `{report_path}`" if report_path else ""

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Sizing complete: {case_name}", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Atlas disk*\n{disk}"},
                {"type": "mrkdwn", "text": f"*Atlas RAM*\n{ram}"},
                {"type": "mrkdwn", "text": f"*Production docs*\n{int(prod_count):,}" if prod_count is not None else "*Production docs*\n—"},
                {"type": "mrkdwn", "text": f"*Compression*\n{compression_pct}"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Numbers from `size_from_dbstats.py` (dbStats scaling only).{path_line}",
                }
            ],
        },
    ]


def load_intake_sla(case_dir: Path) -> int | None:
    intake_path = case_dir / "inputs" / "intake.json"
    if not intake_path.is_file():
        return None
    try:
        data = json.loads(intake_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("queryLatencySlaMs")
