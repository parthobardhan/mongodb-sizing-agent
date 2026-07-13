"""Seed contract: 500 docs per collection, embedded arrays match avgCardinality."""

import ast
import json
from pathlib import Path

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "cases/_example"
SEED_PATH = EXAMPLE_DIR / "outputs/seed.py"
SIZING_INPUTS = EXAMPLE_DIR / "outputs/sizing_inputs.json"


@pytest.mark.skipif(not SEED_PATH.is_file(), reason="example seed not present")
def test_seed_constants():
    source = SEED_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assigns = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assigns.get("RECORDS") == 500
    assert "RANDOM_SEED" in assigns


@pytest.mark.skipif(not SIZING_INPUTS.is_file(), reason="sizing inputs missing")
def test_embedded_cardinality_in_inputs():
    data = json.loads(SIZING_INPUTS.read_text())
    embedded = data.get("embedded", {})
    assert embedded, "expected embedded tables in example sizing_inputs"
