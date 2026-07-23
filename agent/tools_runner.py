"""Invoke Docker, seed, indexes, and sizing scripts via subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from agent.session import read_approval_status
from agent.events import emit_event
from scripts.clear_local_mongo import slugify_use_case
from scripts.sizing_inputs import (
    database_production_document_count,
    load_sizing_inputs,
    sizing_inputs_path as sizing_inputs_file_path,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_TOOLS_ARTIFACTS = ("seed.py", "mongodb_indexes.json", "sizing_inputs.json")


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check, env=env)


def _emit_pipeline_step(step: str, status: str, *, detail: str = "", case: str | None = None) -> None:
    emit_event(
        "pipeline_step",
        step=step,
        status=status,
        detail=detail,
        case=case,
    )


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
    case_name = case_dir.name

    intake = json.loads((case_dir / "inputs" / "intake.json").read_text())
    use_case = intake["useCaseName"]
    db_name = slugify_use_case(use_case)

    _emit_pipeline_step("docker_stack", "running", detail="Starting local MongoDB", case=case_name)
    try:
        run(["bash", "scripts/run_local_stack.sh"])
        _emit_pipeline_step("docker_stack", "ok", case=case_name)
    except subprocess.CalledProcessError:
        _emit_pipeline_step("docker_stack", "fail", case=case_name)
        raise

    seed = case_dir / "outputs" / "seed.py"
    _emit_pipeline_step("seed", "running", detail="500 docs per collection", case=case_name)
    try:
        run([sys.executable, str(seed), "--clear", "--uri", uri])
        _emit_pipeline_step("seed", "ok", case=case_name)
    except subprocess.CalledProcessError:
        _emit_pipeline_step("seed", "fail", case=case_name)
        raise

    _emit_pipeline_step("indexes", "running", detail="Applying mongodb_indexes.json", case=case_name)
    try:
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
        _emit_pipeline_step("indexes", "ok", case=case_name)
    except subprocess.CalledProcessError:
        _emit_pipeline_step("indexes", "fail", case=case_name)
        raise

    inputs_path = sizing_inputs_file_path(case_dir)
    if not inputs_path.is_file():
        raise FileNotFoundError(
            f"Missing {inputs_path} (agent must generate sizing_inputs.json after modeling)"
        )
    sizing_inputs = load_sizing_inputs(inputs_path)
    prod_count = database_production_document_count(sizing_inputs)

    out_json = case_dir / "outputs" / "sizing-report.json"
    _emit_pipeline_step("sizing", "running", detail="dbStats / collStats scaling", case=case_name)
    try:
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
        _emit_pipeline_step("sizing", "ok", case=case_name)
    except subprocess.CalledProcessError:
        _emit_pipeline_step("sizing", "fail", case=case_name)
        raise

    repo_test = case_dir / "outputs" / "test_mongo_repository.py"
    if repo_test.is_file():
        print("Running legacy repository verification tests...", file=sys.stderr)
        _emit_pipeline_step("repository_tests", "running", detail="pytest", case=case_name)
        env = os.environ.copy()
        env.setdefault("MONGODB_URI", uri)
        try:
            run(
                [sys.executable, "-m", "pytest", str(repo_test), "-v"],
                cwd=PROJECT_ROOT,
                env=env,
            )
            _emit_pipeline_step("repository_tests", "ok", case=case_name)
        except subprocess.CalledProcessError:
            _emit_pipeline_step("repository_tests", "fail", case=case_name)
            raise
    else:
        print(
            "Skipping repository tests (outputs/test_mongo_repository.py not present)",
            file=sys.stderr,
        )

    if cleanup:
        _emit_pipeline_step("cleanup", "running", case=case_name)
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
        _emit_pipeline_step("cleanup", "ok", case=case_name)
    elif not no_cleanup and out_json.is_file() and sys.stdin.isatty():
        answer = input(
            f"Clear local MongoDB database `{db_name}`? [y/N] "
        ).strip().lower()
        if answer == "y":
            _emit_pipeline_step("cleanup", "running", case=case_name)
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
            _emit_pipeline_step("cleanup", "ok", case=case_name)

    emit_event("pipeline_finished", report_path=str(out_json), case=case_name)
    return out_json
