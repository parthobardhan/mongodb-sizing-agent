"""Invoke Docker, seed, indexes, and sizing scripts via subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agent.session import read_approval_status
from scripts.clear_local_mongo import slugify_use_case
from scripts.sizing_inputs import (
    database_production_document_count,
    load_sizing_inputs,
    sizing_inputs_path as sizing_inputs_file_path,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_TOOLS_ARTIFACTS = ("seed.py", "mongodb_indexes.json", "sizing_inputs.json")


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check)


def verify_approved(case_dir: Path) -> None:
    status = read_approval_status(case_dir / "outputs" / "data-model.md")
    if status != "approved":
        raise RuntimeError(
            f"data-model.md must be approved before tools (current: {status})"
        )


def missing_tools_artifacts(case_dir: Path) -> list[Path]:
    outputs = case_dir / "outputs"
    return [
        outputs / name
        for name in REQUIRED_TOOLS_ARTIFACTS
        if not (outputs / name).is_file()
    ]


def verify_tools_ready(case_dir: Path) -> None:
    """Require approved data-model.md and Generate-phase outputs before Docker/sizing."""
    verify_approved(case_dir)
    missing = missing_tools_artifacts(case_dir)
    if missing:
        names = ", ".join(p.name for p in missing)
        raise FileNotFoundError(
            f"Generate-phase artifacts required before tools (missing: {names})"
        )


def run_tools_pipeline(
    case_dir: Path,
    *,
    uri: str | None = None,
    cleanup: bool = False,
    no_cleanup: bool = False,
) -> Path:
    verify_tools_ready(case_dir)
    uri = uri or os.environ.get("MONGODB_URI", "mongodb://localhost:27017")

    intake = __import__("json").loads((case_dir / "inputs" / "intake.json").read_text())
    use_case = intake["useCaseName"]
    db_name = slugify_use_case(use_case)

    run(["bash", "scripts/run_local_stack.sh"])

    seed = case_dir / "outputs" / "seed.py"
    run([sys.executable, str(seed), "--clear", "--uri", uri])

    run(
        [
            sys.executable,
            "scripts/apply_indexes.py",
            "--uri",
            uri,
            "--case",
            str(case_dir),
        ]
    )

    inputs_path = sizing_inputs_file_path(case_dir)
    if not inputs_path.is_file():
        raise FileNotFoundError(
            f"Missing {inputs_path} (agent must generate sizing_inputs.json after modeling)"
        )
    sizing_inputs = load_sizing_inputs(inputs_path)
    prod_count = database_production_document_count(sizing_inputs)

    out_json = case_dir / "outputs" / "sizing-report.json"
    run(
        [
            sys.executable,
            "scripts/size_from_dbstats.py",
            "--uri",
            uri,
            "--db",
            db_name,
            "--production-count",
            str(prod_count),
            "--sizing-inputs-file",
            str(inputs_path),
            "--out",
            str(out_json),
        ]
    )

    if cleanup:
        run(
            [
                sys.executable,
                "scripts/clear_local_mongo.py",
                "--uri",
                uri,
                "--use-case",
                use_case,
            ]
        )
    elif not no_cleanup and out_json.is_file():
        answer = input(
            f"Clear local MongoDB database `{db_name}`? [y/N] "
        ).strip().lower()
        if answer == "y":
            run(
                [
                    sys.executable,
                    "scripts/clear_local_mongo.py",
                    "--uri",
                    uri,
                    "--use-case",
                    use_case,
                ]
            )

    return out_json
