"""Derive dashboard phase and artifact state from case outputs on disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.session import read_approval_status

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PHASES = (
    "intake",
    "model",
    "sizing_gate",
    "approval",
    "generate",
    "tools",
)

ARTIFACT_NAMES = (
    "data-model.md",
    "sizing_inputs.json",
    "session.json",
    "seed.py",
    "mongodb_indexes.json",
    "mongo_repository.py",
    "test_mongo_repository.py",
    "sizing-report.json",
    "sizing-report.md",
)

PREVIEW_ARTIFACTS = frozenset({"data-model.md", "sizing-report.md"})


def case_dir_for(use_case: str) -> Path:
    return PROJECT_ROOT / "cases" / use_case


def _mtime_iso(path: Path) -> str | None:
    if not path.is_file():
        return None
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _load_session(outputs: Path) -> dict[str, Any]:
    path = outputs / "session.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_sizing_atlas(outputs: Path) -> dict[str, Any] | None:
    path = outputs / "sizing-report.json"
    if not path.is_file():
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    atlas = report.get("atlas") or {}
    disk = atlas.get("diskRequired")
    ram = atlas.get("ramRequired")
    if disk is None and ram is None:
        return None
    return {
        "diskRequired": disk,
        "ramRequired": ram,
        "diskRequiredGb": round(disk / (1024**3), 2) if disk else None,
        "ramRequiredGb": round(ram / (1024**3), 2) if ram else None,
    }


def derive_phase_status(outputs: Path) -> dict[str, str]:
    """Return per-phase status: pending | active | done."""
    data_model = outputs / "data-model.md"
    sizing_inputs = outputs / "sizing_inputs.json"
    seed = outputs / "seed.py"
    indexes = outputs / "mongodb_indexes.json"
    report = outputs / "sizing-report.json"

    approval = read_approval_status(data_model)
    intake_done = (outputs.parent / "inputs" / "intake.json").is_file()
    model_done = data_model.is_file()
    sizing_gate_done = sizing_inputs.is_file()
    approval_done = approval == "approved"
    generate_done = seed.is_file() and indexes.is_file()
    tools_done = report.is_file()

    flags = {
        "intake": intake_done,
        "model": model_done,
        "sizing_gate": sizing_gate_done,
        "approval": approval_done,
        "generate": generate_done,
        "tools": tools_done,
    }

    statuses: dict[str, str] = {}
    active_assigned = False
    for phase in PHASES:
        if flags[phase]:
            statuses[phase] = "done"
        elif not active_assigned:
            statuses[phase] = "active"
            active_assigned = True
        else:
            statuses[phase] = "pending"

    if tools_done:
        for phase in PHASES:
            if flags[phase]:
                statuses[phase] = "done"

    return statuses


def build_case_state(use_case: str) -> dict[str, Any]:
    case_dir = case_dir_for(use_case)
    outputs = case_dir / "outputs"
    data_model = outputs / "data-model.md"
    approval = read_approval_status(data_model)
    session = _load_session(outputs)

    artifacts: list[dict[str, Any]] = []
    for name in ARTIFACT_NAMES:
        path = outputs / name
        artifacts.append(
            {
                "name": name,
                "exists": path.is_file(),
                "mtime": _mtime_iso(path),
                "previewable": name in PREVIEW_ARTIFACTS,
            }
        )

    mode = "agent" if approval == "approved" else "plan"

    return {
        "case": use_case,
        "agentId": session.get("agent_id"),
        "lastRunId": session.get("last_run_id"),
        "approvalStatus": approval,
        "mode": mode,
        "phases": derive_phase_status(outputs),
        "artifacts": artifacts,
        "atlas": _load_sizing_atlas(outputs),
    }


def read_artifact(use_case: str, name: str) -> str | None:
    if name not in PREVIEW_ARTIFACTS:
        return None
    path = case_dir_for(use_case) / "outputs" / name
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
