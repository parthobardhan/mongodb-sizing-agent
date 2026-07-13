import pytest
from pymongo import ASCENDING, DESCENDING

from scripts.apply_indexes import keys_to_pymongo


def test_keys_to_pymongo_asc_desc():
    assert keys_to_pymongo([["cKey", 1]]) == [("cKey", ASCENDING)]
    assert keys_to_pymongo([["cKey", -1]]) == [("cKey", DESCENDING)]
    assert keys_to_pymongo([["a", "asc"], ["b", "desc"]]) == [
        ("a", ASCENDING),
        ("b", DESCENDING),
    ]


def test_keys_to_pymongo_invalid_raises():
    with pytest.raises(ValueError, match="Invalid key spec"):
        keys_to_pymongo(["not-a-pair"])
