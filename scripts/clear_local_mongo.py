#!/usr/bin/env python3
"""Drop case sizing database or tear down docker compose."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from pymongo import MongoClient


def slugify_use_case(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"sizing_{slug}"


def drop_database(uri: str, db_name: str) -> None:
    client = MongoClient(uri)
    client.drop_database(db_name)
    client.close()
    print(f"Dropped database: {db_name}")


def teardown_compose(project_root: Path) -> None:
    subprocess.run(
        ["docker", "compose", "down", "-v"],
        cwd=project_root,
        check=True,
    )
    print("docker compose down -v completed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--use-case", required=True, help="useCaseName from intake")
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="docker compose down -v instead of dropDatabase",
    )
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parent.parent
    if args.teardown:
        teardown_compose(project_root)
        return 0

    db_name = slugify_use_case(args.use_case)
    drop_database(args.uri, db_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
