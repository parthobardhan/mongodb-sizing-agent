#!/usr/bin/env python3
"""Create indexes from mongodb_indexes.json (no runtime dedup)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pymongo import ASCENDING, DESCENDING, MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.index_utils import assert_no_redundant_prefix_indexes

DIRECTION = {1: ASCENDING, -1: DESCENDING, "asc": ASCENDING, "desc": DESCENDING}


def keys_to_pymongo(keys: list) -> list[tuple[str, int]]:
    out = []
    for item in keys:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            field, direction = item[0], item[1]
            out.append((field, DIRECTION.get(direction, direction)))
        else:
            raise ValueError(f"Invalid key spec: {item}")
    return out


def apply_indexes(uri: str, spec_path: Path, database: str | None = None) -> int:
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    assert_no_redundant_prefix_indexes(spec)

    db_name = database or spec.get("database")
    if not db_name:
        raise ValueError("database name required in spec or --db")

    client = MongoClient(uri)
    db = client[db_name]
    created = 0
    for idx in spec.get("indexes", []):
        collection = db[idx["collection"]]
        keys = keys_to_pymongo(idx["keys"])
        options = dict(idx.get("options") or {})
        collection.create_index(keys, **options)
        created += 1
    client.close()
    print(f"Created {created} index(es) on {db_name}")
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--case", type=Path, help="Case dir; uses outputs/mongodb_indexes.json")
    parser.add_argument("--spec", type=Path, help="Path to mongodb_indexes.json")
    parser.add_argument("--db", help="Override database name")
    args = parser.parse_args(argv)

    if args.case:
        spec_path = args.case / "outputs" / "mongodb_indexes.json"
    elif args.spec:
        spec_path = args.spec
    else:
        print("error: --case or --spec required", file=sys.stderr)
        return 1

    if not spec_path.is_file():
        print(f"error: {spec_path} not found", file=sys.stderr)
        return 1

    apply_indexes(args.uri, spec_path, args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
