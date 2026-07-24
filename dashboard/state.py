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
    "plan",
    "design",
    "approval",
    "code",
    "test",
    "sizing",
    "output",
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


def _has_legacy(outputs: Path) -> bool:
    legacy_dir = outputs.parent / "inputs" / "legacy"
    return legacy_dir.is_dir() and any(legacy_dir.iterdir())


def _output_complete(outputs: Path, *, has_legacy: bool) -> bool:
    required = (
        "data-model.md",
        "sizing_inputs.json",
        "session.json",
        "seed.py",
        "mongodb_indexes.json",
        "sizing-report.json",
        "sizing-report.md",
    )
    if has_legacy:
        required = required + ("mongo_repository.py", "test_mongo_repository.py")
    return all((outputs / name).is_file() for name in required)


def _phase_completion_flags(outputs: Path) -> dict[str, bool]:
    data_model = outputs / "data-model.md"
    sizing_inputs = outputs / "sizing_inputs.json"
    seed = outputs / "seed.py"
    indexes = outputs / "mongodb_indexes.json"
    mongo_repo = outputs / "mongo_repository.py"
    test_repo = outputs / "test_mongo_repository.py"
    report_json = outputs / "sizing-report.json"
    report_md = outputs / "sizing-report.md"
    has_legacy = _has_legacy(outputs)

    approval = read_approval_status(data_model)
    code_done = seed.is_file() and indexes.is_file()
    if has_legacy:
        code_done = code_done and mongo_repo.is_file()

    return {
        "intake": (outputs.parent / "inputs" / "intake.json").is_file(),
        "plan": data_model.is_file(),
        "design": sizing_inputs.is_file(),
        "approval": approval == "approved",
        "code": code_done,
        "test": test_repo.is_file() or not has_legacy,
        "sizing": report_json.is_file() and report_md.is_file(),
        "output": _output_complete(outputs, has_legacy=has_legacy),
    }


def derive_phase_status(outputs: Path) -> dict[str, str]:
    """Return per-phase status: pending | active | done."""
    flags = _phase_completion_flags(outputs)

    statuses: dict[str, str] = {
        phase: "done" if flags[phase] else "pending" for phase in PHASES
    }

    for phase in PHASES:
        if not flags[phase]:
            statuses[phase] = "active"
            break

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
