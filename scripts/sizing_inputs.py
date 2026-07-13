"""Validate and derive intake.json / sizing_inputs.json fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


def _schema_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "templates" / name


def load_schema(name: str) -> dict[str, Any]:
    with open(_schema_path(name), encoding="utf-8") as f:
        return json.load(f)


def validate_intake(data: dict[str, Any]) -> None:
    jsonschema.validate(data, load_schema("intake.schema.json"))


def load_intake(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    validate_intake(data)
    return data


def sizing_inputs_path(case_dir: Path) -> Path:
    """Agent-generated sizing metadata lives under case outputs."""
    return case_dir / "outputs" / "sizing_inputs.json"


def validate_sizing_inputs(data: dict[str, Any]) -> None:
    jsonschema.validate(data, load_schema("sizing_inputs.schema.json"))


def derive_embedded_cardinality(
    parent_production_count: int,
    child_production_count: int,
) -> dict[str, Any]:
    """Derive avgCardinality and ratioLabel from parent/child production row counts."""
    if parent_production_count <= 0:
        raise ValueError("parent_production_count must be positive")
    avg = child_production_count / parent_production_count
    return {
        "avgCardinality": avg,
        "ratioLabel": f"{parent_production_count}:{child_production_count}",
        "derivedFrom": {
            "parentProductionCount": parent_production_count,
            "childProductionCount": child_production_count,
            "method": "childProductionCount / parentProductionCount",
        },
    }


def load_sizing_inputs(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    validate_sizing_inputs(data)
    return data


def database_production_document_count(data: dict[str, Any]) -> int:
    explicit = data.get("databaseProductionDocumentCount")
    if explicit is not None:
        return int(explicit)
    collections = data.get("collections", {})
    return sum(int(c.get("productionDocumentCount", 0)) for c in collections.values())
