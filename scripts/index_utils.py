"""Compound index prefix validation for mongodb_indexes.json."""

from __future__ import annotations

from typing import Any


def index_key_fields(keys: list[list[Any]]) -> list[str]:
    return [k[0] if isinstance(k, (list, tuple)) else str(k) for k in keys]


def options_signature(options: dict[str, Any] | None) -> tuple:
    opts = options or {}
    return (
        opts.get("unique", False),
        opts.get("sparse", False),
        opts.get("partialFilterExpression"),
        opts.get("type"),
    )


def is_strict_prefix(shorter: list[str], longer: list[str]) -> bool:
    if len(shorter) >= len(longer):
        return False
    return longer[: len(shorter)] == shorter


def find_redundant_prefix_indexes(indexes: list[dict[str, Any]]) -> list[str]:
    """
    Return human-readable descriptions of redundant prefix indexes per collection.
    Two indexes conflict when same collection, same options signature, and one's
    key fields are a strict prefix of the other's.
    """
    redundancies: list[str] = []
    by_collection: dict[str, list[dict[str, Any]]] = {}
    for idx in indexes:
        by_collection.setdefault(idx["collection"], []).append(idx)

    for collection, col_indexes in by_collection.items():
        for i, a in enumerate(col_indexes):
            fields_a = index_key_fields(a["keys"])
            sig_a = options_signature(a.get("options"))
            name_a = (a.get("options") or {}).get("name", str(fields_a))
            for b in col_indexes[i + 1 :]:
                fields_b = index_key_fields(b["keys"])
                sig_b = options_signature(b.get("options"))
                if sig_a != sig_b:
                    continue
                name_b = (b.get("options") or {}).get("name", str(fields_b))
                if is_strict_prefix(fields_a, fields_b):
                    redundancies.append(
                        f"{collection}: '{name_a}' is prefix of '{name_b}'"
                    )
                elif is_strict_prefix(fields_b, fields_a):
                    redundancies.append(
                        f"{collection}: '{name_b}' is prefix of '{name_a}'"
                    )
    return redundancies


def assert_no_redundant_prefix_indexes(spec: dict[str, Any]) -> None:
    redundancies = find_redundant_prefix_indexes(spec.get("indexes", []))
    if redundancies:
        raise ValueError(
            "Redundant prefix indexes detected:\n" + "\n".join(redundancies)
        )
