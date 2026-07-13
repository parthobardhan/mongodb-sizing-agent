#!/usr/bin/env python3
"""Optional helper: parse simple SQL CREATE INDEX statements to index spec fragments."""

from __future__ import annotations

import re
from typing import Any


CREATE_INDEX_RE = re.compile(
    r"CREATE\s+(UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(([^)]+)\)",
    re.IGNORECASE,
)


def parse_create_index(sql: str) -> dict[str, Any] | None:
    m = CREATE_INDEX_RE.search(sql.strip())
    if not m:
        return None
    unique, name, table, cols = m.groups()
    fields = [c.strip().split()[0] for c in cols.split(",")]
    keys = [[f, 1] for f in fields]
    return {
        "collection": table.lower(),
        "keys": keys,
        "options": {"name": name, "unique": bool(unique)},
        "sourceTable": table,
    }


def _strip_sql_comments(sql: str) -> str:
    """Remove ``--`` line comments so leading comments don't hide statements."""
    lines = [re.sub(r"--.*$", "", line) for line in sql.splitlines()]
    return "\n".join(lines)


def parse_sql_file(path: str) -> list[dict[str, Any]]:
    from pathlib import Path

    text = Path(path).read_text(encoding="utf-8")
    results = []
    for segment in text.split(";"):
        segment = _strip_sql_comments(segment).strip()
        if not segment:
            continue
        parsed = parse_create_index(segment)
        if parsed:
            results.append(parsed)
    return results
