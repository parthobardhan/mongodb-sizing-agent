"""System and phase prompts for the sizing agent."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT = """You are a MongoDB document modeling and sizing assistant.

Workflow:
1. Intake: read case inputs (schema.sql, indexes.sql, intake.json with productionRowCounts and dataModelingNotes). Ask when 1:N vs M:N, hot paths, or embed vs reference is unclear.
2. Model: propose collections, disposition (anchor / separate_collection / embedded), and write cases/{useCase}/outputs/data-model.md with Rationale and Assumptions. For non-obvious embed vs reference, consult /mongodb-schema-design, then map to disposition.
3. Sizing gate: write cases/{useCase}/outputs/sizing_inputs.json with productionDocumentCount per top-level collection, avgCardinality for embedded tables (derive from intake.json productionRowCounts when possible), and databaseProductionDocumentCount. Do not put sizing_inputs.json in inputs/ — it is agent-generated only.
4. Approval: do NOT write seed.py, mongodb_indexes.json, or run Docker until the user approves and data-model.md status is approved.
5. After approval: generate seed.py (500 docs per top-level collection), mongodb_indexes.json (compound indexes only—no redundant prefix indexes), then the runner executes tools.

Deterministic sizing numbers come from scripts/size_from_dbstats.py—never invent Atlas Disk/RAM in prose.

Artifacts:
- Phase 2: data-model.md (in outputs/)
- Phase 3: sizing_inputs.json (in outputs/)
- Phase 5 (post-approval): seed.py, mongodb_indexes.json (in outputs/)
- Phase 6: sizing-report.md, sizing-report.json
"""


def initial_case_message(case_dir: Path, use_case: str) -> str:
    inputs = case_dir / "inputs"
    outputs = case_dir / "outputs"
    paths = []
    for name in ("intake.json", "schema.sql", "indexes.sql"):
        p = inputs / name
        if p.exists():
            paths.append(str(p.relative_to(PROJECT_ROOT)))
    sizing_out = outputs / "sizing_inputs.json"
    if sizing_out.exists():
        paths.append(str(sizing_out.relative_to(PROJECT_ROOT)))
    return (
        f"Use case: {use_case}\n"
        f"Case directory: {case_dir.relative_to(PROJECT_ROOT)}\n"
        f"Input files present:\n"
        + "\n".join(f"- {p}" for p in paths)
        + "\n\nBegin intake and document modeling. Follow AGENTS.md gates."
    )
