"""Unit tests for storage stats settling before sizing."""

from scripts.size_from_dbstats import (
    _has_minimum_page_only,
    _stats_fingerprint,
)


def test_stats_fingerprint_includes_per_collection_storage():
    db_stats = {"storageSize": 100_000, "indexSize": 20_000}
    coll_list = [
        {
            "ns": "db.customers",
            "storageSize": 143_360,
            "totalIndexSize": 69_632,
        },
        {
            "ns": "db.orders",
            "storageSize": 200_000,
            "totalIndexSize": 50_000,
        },
    ]
    fp = _stats_fingerprint(db_stats, coll_list)
    assert fp[0] == 100_000
    assert fp[1] == 20_000
    assert fp[2] == (
        ("customers", 143_360, 69_632),
        ("orders", 200_000, 50_000),
    )


def test_has_minimum_page_only_detects_stale_collstats():
    stale = [
        {
            "ns": "db.customers",
            "count": 500,
            "size": 460_646,
            "storageSize": 4096,
            "totalIndexSize": 53_248,
        }
    ]
    settled = [
        {
            "ns": "db.customers",
            "count": 500,
            "size": 460_646,
            "storageSize": 143_360,
            "totalIndexSize": 69_632,
        }
    ]
    assert _has_minimum_page_only(stale) is True
    assert _has_minimum_page_only(settled) is False


def test_has_minimum_page_only_ignores_small_collections():
    coll_list = [
        {
            "ns": "db.order_tags",
            "count": 500,
            "size": 4000,
            "storageSize": 4096,
            "totalIndexSize": 4096,
        }
    ]
    assert _has_minimum_page_only(coll_list) is False
