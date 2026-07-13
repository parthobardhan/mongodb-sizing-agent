from pathlib import Path

from scripts.sql_index_parser import parse_create_index, parse_sql_file


def test_parse_create_index_simple():
    sql = "CREATE INDEX idx_history_ckey ON CLIENT_DOCUMENT_HISTORY (cKey)"
    result = parse_create_index(sql)
    assert result is not None
    assert result["collection"] == "client_document_history"
    assert result["keys"] == [["cKey", 1]]
    assert result["options"]["name"] == "idx_history_ckey"
    assert result["options"]["unique"] is False


def test_parse_create_index_unique():
    sql = (
        "CREATE UNIQUE INDEX idx_release_composite "
        "ON CLIENT_RELEASE_TABLE (cKey, cKey_Type, cCopy_Number)"
    )
    result = parse_create_index(sql)
    assert result is not None
    assert result["collection"] == "client_release_table"
    assert result["options"]["unique"] is True
    assert len(result["keys"]) == 3


def test_parse_create_index_returns_none_on_invalid():
    assert parse_create_index("SELECT 1") is None
    assert parse_create_index("") is None


def test_parse_sql_file_from_example(example_case_dir: Path):
    path = example_case_dir / "inputs" / "indexes.sql"
    results = parse_sql_file(str(path))
    assert len(results) >= 1
    collections = {r["collection"] for r in results}
    assert "client_document_history" in collections or "client_release_table" in collections
