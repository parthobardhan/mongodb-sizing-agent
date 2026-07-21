"""Resume Cursor agent after Slack/data-model approval to generate Phase 5 artifacts."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from agent.events import emit_event
from agent.session import load_session, resume_agent, save_session, send_and_wait
from agent.tools_runner import missing_tools_artifacts

logger = logging.getLogger(__name__)

ContinueStatus = Literal["ok", "no_session", "still_missing", "error"]


@dataclass
class ContinueResult:
    status: ContinueStatus
    agent_id: str | None = None
    missing: list[str] = field(default_factory=list)
    error: str | None = None


def _resolve_use_case(case_dir: Path) -> str:
    intake = case_dir / "inputs" / "intake.json"
    if intake.is_file():
        try:
            return json.loads(intake.read_text(encoding="utf-8"))["useCaseName"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    return case_dir.name


def _has_legacy_inputs(case_dir: Path) -> bool:
    legacy = case_dir / "inputs" / "legacy"
    if not legacy.is_dir():
        return False
    return any(p.is_file() for p in legacy.iterdir())


def build_continue_prompt(
    *,
    use_case: str,
    approver: str,
    case_dir: Path,
) -> str:
    """Phase 5 generate-only prompt after data-model approval."""
    outputs_rel = f"cases/{case_dir.name}/outputs"
    lines = [
        f"{approver} approved the data model for use case `{use_case}`.",
        "",
        f"`{outputs_rel}/data-model.md` is already approved. Do not change the approval status.",
        "",
        f"Phase 5 only — generate these artifacts under `{outputs_rel}/`:",
        "- `seed.py` (500 documents per top-level collection; follow the seed-and-index skill)",
        "- `mongodb_indexes.json` (one compound index per relational composite; "
        "no redundant compound prefixes)",
    ]
    if _has_legacy_inputs(case_dir):
        lines.append(
            "- `mongo_repository.py` and `test_mongo_repository.py` "
            "(legacy-repo-migration skill; `inputs/legacy/*` is present)"
        )
    lines.extend(
        [
            "",
            "Do NOT:",
            "- start Docker / `run_local_stack.sh`",
            "- execute `seed.py`",
            "- run `apply_indexes.py`",
            "- run `size_from_dbstats.py`",
            "",
            "The host will run the tools pipeline after these files exist. "
            "Follow AGENTS.md and existing skills.",
        ]
    )
    return "\n".join(lines)


def continue_generate_after_approval(
    case_dir: Path,
    *,
    approver: str,
    use_case: str | None = None,
) -> ContinueResult:
    """Resume the case agent in agent mode and ask it to write generate-phase files.

    Does not create a new agent when session.json is missing. Does not run tools.
    """
    outputs = case_dir / "outputs"
    resolved_use_case = use_case or _resolve_use_case(case_dir)
    agent_id = load_session(outputs)
    if not agent_id:
        error = (
            f"Cannot resume Cursor agent: no agent_id in `{outputs / 'session.json'}`. "
            "Start or resume the sizing agent for this case so a session is saved, "
            "then approve again."
        )
        logger.error("%s (case=%s)", error, case_dir.name)
        emit_event(
            "continuation_failed",
            case=resolved_use_case,
            reason="no_session",
        )
        return ContinueResult(status="no_session", error=error)

    prompt = build_continue_prompt(
        use_case=resolved_use_case,
        approver=approver,
        case_dir=case_dir,
    )

    try:
        agent = resume_agent(agent_id)
        with agent:
            try:
                send_and_wait(agent, prompt, mode="agent")
            finally:
                save_session(outputs, agent.agent_id)
    except Exception as exc:
        logger.exception(
            "Agent continuation failed for %s (agent_id=%s): %s",
            case_dir.name,
            agent_id,
            exc,
        )
        emit_event(
            "continuation_failed",
            case=resolved_use_case,
            agent_id=agent_id,
            error=str(exc),
        )
        return ContinueResult(status="error", agent_id=agent_id, error=str(exc))

    missing = missing_tools_artifacts(case_dir)
    if missing:
        names = [p.name for p in missing]
        logger.warning(
            "Generate artifacts still missing after continuation for %s: %s",
            case_dir.name,
            ", ".join(names),
        )
        return ContinueResult(
            status="still_missing",
            agent_id=agent_id,
            missing=names,
        )

    return ContinueResult(status="ok", agent_id=agent_id)
