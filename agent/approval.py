"""Write approval status into data-model.md (Slack / dashboard actuators)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from agent.session import read_approval_status

_HEADER_STATUS_RE = re.compile(
    r"^(\*\*Approval status:\*\*\s*)(approved|pending)(\s*)$",
    re.IGNORECASE | re.MULTILINE,
)
_FOOTER_STATUS_RE = re.compile(
    r"^(-\s*Status:\s*\*\*)(approved|pending)(\*\*\s*)$",
    re.IGNORECASE | re.MULTILINE,
)
_APPROVED_AT_RE = re.compile(
    r"^-\s*Approved at:.*$",
    re.IGNORECASE | re.MULTILINE,
)
_APPROVED_BY_RE = re.compile(
    r"^-\s*Approved by:.*$",
    re.IGNORECASE | re.MULTILINE,
)
_VIA_RE = re.compile(
    r"^-\s*Via:.*$",
    re.IGNORECASE | re.MULTILINE,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def approve_data_model(data_model_path: Path, approver: str) -> str:
    """Flip approval status to approved and append audit lines. Returns new status."""
    if not data_model_path.is_file():
        raise FileNotFoundError(f"data-model.md not found: {data_model_path}")

    text = data_model_path.read_text(encoding="utf-8")
    if not _HEADER_STATUS_RE.search(text) and not _FOOTER_STATUS_RE.search(text):
        raise ValueError("data-model.md has no approval status line to update")

    current = read_approval_status(data_model_path)
    if current == "approved":
        return "approved"

    updated = _HEADER_STATUS_RE.sub(r"\1approved\3", text, count=1)
    updated = _FOOTER_STATUS_RE.sub(r"\1approved\3", updated, count=1)

    stamp = _utc_now_iso()
    audit_lines = [
        f"- Approved at: {stamp}",
        f"- Approved by: {approver}",
        "- Via: Slack",
    ]

    if "## 10. Approval" in updated or "## 10. approval" in updated.lower():
        updated = _APPROVED_AT_RE.sub("", updated)
        updated = _APPROVED_BY_RE.sub("", updated)
        updated = _VIA_RE.sub("", updated)
        updated = re.sub(r"\n{3,}", "\n\n", updated.rstrip()) + "\n"
        updated = updated.rstrip() + "\n" + "\n".join(audit_lines) + "\n"
    else:
        updated = updated.rstrip() + "\n\n## 10. Approval\n\n"
        updated += "- Status: **approved**\n"
        updated += "\n".join(audit_lines) + "\n"

    data_model_path.write_text(updated, encoding="utf-8")
    return read_approval_status(data_model_path)
