from pathlib import Path

from scripts.sizing_inputs import (
    database_production_document_count,
    load_sizing_inputs,
    sizing_inputs_path,
)


def test_database_production_document_count_explicit():
    data = {
        "collections": {
            "a": {"productionDocumentCount": 100},
            "b": {"productionDocumentCount": 200},
        },
        "databaseProductionDocumentCount": 999,
    }
    assert database_production_document_count(data) == 999


def test_database_production_document_count_sums_collections():
    data = {
        "collections": {
            "a": {"productionDocumentCount": 100},
            "b": {"productionDocumentCount": 250},
        },
    }
    assert database_production_document_count(data) == 350


def test_load_sizing_inputs_validates(example_case_dir: Path):
    path = sizing_inputs_path(example_case_dir)
    data = load_sizing_inputs(path)
    assert data["databaseProductionDocumentCount"] == 20_000_000
    assert "client_document_history" in data["collections"]
