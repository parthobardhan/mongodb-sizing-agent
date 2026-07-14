#!/usr/bin/env python3
"""CLI: MongoDB sizing agent (Cursor SDK) + deterministic tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from agent.prompts import SYSTEM_PROMPT, initial_case_message
from scripts.sizing_inputs import validate_intake

# cursor_sdk is an optional dependency: agent.session (and, transitively,
# agent.tools_runner) import it at module scope. Guard the import here so a
# missing SDK produces a friendly message from main() instead of crashing at
# import time.
try:
    from cursor_sdk import CursorAgentError
    from agent.session import (
        create_agent,
        initial_send_mode,
        load_session,
        read_approval_status,
        resume_agent,
        save_session,
        send_and_wait,
    )
    from agent.tools_runner import missing_tools_artifacts, run_tools_pipeline

    _SDK_IMPORT_ERROR: ImportError | None = None
except ImportError as exc:
    _SDK_IMPORT_ERROR = exc


def case_dir_for(use_case: str) -> Path:
    return PROJECT_ROOT / "cases" / use_case


def load_intake(case_dir: Path) -> dict:
    path = case_dir / "inputs" / "intake.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    validate_intake(data)
    return data


def cmd_interactive(case_dir: Path, use_case: str, resume_id: str | None) -> int:
    outputs = case_dir / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    agent_id = resume_id or load_session(outputs)
    if agent_id:
        agent = resume_agent(agent_id)
        print(f"Resumed agent {agent_id}", file=sys.stderr)
    else:
        agent = create_agent()
        save_session(outputs, agent.agent_id)

    data_model_path = outputs / "data-model.md"
    mode = initial_send_mode(data_model_path)

    with agent:
        if not agent_id:
            try:
                send_and_wait(agent, SYSTEM_PROMPT, mode=mode)
                send_and_wait(agent, initial_case_message(case_dir, use_case), mode=mode)
            except CursorAgentError as exc:
                print(f"SDK error during bootstrap: {exc}", file=sys.stderr)
                save_session(outputs, agent.agent_id)
                return 1
            save_session(outputs, agent.agent_id)

        while True:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                break

            if user_input.lower() == "approve":
                mode = "agent"
            try:
                send_and_wait(agent, user_input, mode=mode)
            except CursorAgentError as exc:
                print(f"SDK error: {exc}", file=sys.stderr)
                save_session(outputs, agent.agent_id)
                continue
            save_session(outputs, agent.agent_id)

            status = read_approval_status(data_model_path)
            if status == "approved" and user_input.lower() in (
                "run tools",
                "tools",
                "approve",
            ):
                missing = missing_tools_artifacts(case_dir)
                if missing:
                    names = ", ".join(p.name for p in missing)
                    print(
                        f"Generate artifacts not ready yet ({names}). "
                        "Type 'run tools' after seed/indexes are written.",
                        file=sys.stderr,
                    )
                    continue
                print("Running tools pipeline...", file=sys.stderr)
                run_tools_pipeline(case_dir)
                break

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MongoDB sizing agent")
    parser.add_argument("--case", required=True, help="Case folder name under cases/")
    parser.add_argument("--resume", help="Agent ID to resume")
    parser.add_argument(
        "--phase",
        choices=("interactive", "tools-only"),
        default="interactive",
    )
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--no-cleanup", action="store_true")
    args = parser.parse_args(argv)

    if _SDK_IMPORT_ERROR is not None:
        print(
            f"error: cursor-sdk not installed ({_SDK_IMPORT_ERROR})",
            file=sys.stderr,
        )
        return 1

    case_dir = case_dir_for(args.case)
    if not case_dir.is_dir():
        print(f"error: case not found: {case_dir}", file=sys.stderr)
        return 1

    load_intake(case_dir)

    if args.phase == "tools-only":
        run_tools_pipeline(
            case_dir,
            cleanup=args.cleanup,
            no_cleanup=args.no_cleanup,
        )
        return 0

    try:
        return cmd_interactive(case_dir, args.case, args.resume)
    except CursorAgentError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
