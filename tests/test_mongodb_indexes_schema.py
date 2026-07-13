import json
from pathlib import Path

import pytest

from scripts.index_utils import assert_no_redundant_prefix_indexes, find_redundant_prefix_indexes

EXAMPLE_INDEXES = Path(__file__).resolve().parent.parent / "cases/_example/outputs/mongodb_indexes.json"


class TestPrefixIndexes:
    def test_example_has_no_redundant_prefixes(self):
        if not EXAMPLE_INDEXES.is_file():
            pytest.skip("example indexes not committed")
        spec = json.loads(EXAMPLE_INDEXES.read_text())
        assert_no_redundant_prefix_indexes(spec)

    def test_detects_redundant_prefix(self):
        spec = {
            "indexes": [
                {
                    "collection": "orders",
                    "keys": [["cKey", 1]],
                    "options": {"name": "cKey"},
                },
                {
                    "collection": "orders",
                    "keys": [["cKey", 1], ["cKey_Type", 1]],
                    "options": {"name": "cKey_type"},
                },
            ]
        }
        redundancies = find_redundant_prefix_indexes(spec["indexes"])
        assert len(redundancies) == 1
        with pytest.raises(ValueError):
            assert_no_redundant_prefix_indexes(spec)

    def test_different_options_not_redundant(self):
        spec = {
            "indexes": [
                {
                    "collection": "orders",
                    "keys": [["cKey", 1]],
                    "options": {"name": "cKey_nonunique"},
                },
                {
                    "collection": "orders",
                    "keys": [["cKey", 1], ["cKey_Type", 1]],
                    "options": {"name": "cKey_type_unique", "unique": True},
                },
            ]
        }
        assert find_redundant_prefix_indexes(spec["indexes"]) == []
