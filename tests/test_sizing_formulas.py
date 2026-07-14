"""TDD: dbStats Atlas formulas + per-collection collStats scaling."""

import pytest

from scripts.size_from_dbstats import (
    build_report,
    compute_collection_scaling,
    compute_dbstats_scaling,
)


class TestDbStatsScaling:
    def test_compression_and_production_metrics(self):
        db_stats = {
            "objects": 500,
            "avgObjSize": 2048,
            "dataSize": 1_000_000,
            "storageSize": 800_000,
            "indexSize": 200_000,
        }
        prod = 20_000_000
        result = compute_dbstats_scaling(db_stats, prod)

        assert result["compression"] == pytest.approx(0.2)
        assert result["dataSizeProduction"] == 2048 * prod
        assert result["storageSizeProduction"] == pytest.approx(
            (800_000 / 500) * prod
        )
        assert result["indexSizeProduction"] == pytest.approx((200_000 / 500) * prod)
        assert result["ramUsage"] == pytest.approx(result["indexSizeProduction"] * 1.5)
        assert result["diskRequired"] == pytest.approx(
            result["storageSizeProduction"] / 0.75
        )
        assert result["ramRequired"] == result["ramUsage"]
        assert result["sizingBasis"] == "measured-storage"
        assert "warning" not in result

    def test_tiny_sample_uses_data_size_floor_for_disk(self):
        """500-doc samples often report ~one WT page for storageSize."""
        from scripts.size_from_dbstats import ASSUMED_STORAGE_TO_DATA_RATIO

        db_stats = {
            "objects": 500,
            "avgObjSize": 297.58,
            "dataSize": 290_000,
            "storageSize": 4096,
            "indexSize": 56_000,
        }
        prod = 20_000_000
        result = compute_dbstats_scaling(db_stats, prod)

        floor_storage = result["dataSizeProduction"] * ASSUMED_STORAGE_TO_DATA_RATIO
        measured_storage = (4096 / 500) * prod
        assert floor_storage > measured_storage
        assert result["sizingBasis"] == "data-size-floor"
        assert result["storageSizeProduction"] == pytest.approx(floor_storage)
        assert result["diskRequired"] == pytest.approx(floor_storage / 0.75)
        assert result["diskRequired"] >= result["dataSizeProduction"] * ASSUMED_STORAGE_TO_DATA_RATIO / 0.75
        assert "warning" in result

    def test_zero_data_size_compression_guard(self):
        db_stats = {"objects": 10, "dataSize": 0, "storageSize": 0, "indexSize": 0}
        result = compute_dbstats_scaling(db_stats, 1_000)
        assert result["compression"] is None

    def test_zero_objects_warning(self):
        db_stats = {"objects": 0, "dataSize": 0, "storageSize": 0, "indexSize": 0}
        result = compute_dbstats_scaling(db_stats, 1_000)
        assert "warning" in result
        assert result["diskRequired"] == 0
        assert result["sizingBasis"] == "measured-storage"


class TestCollStatsScaling:
    def test_per_collection_production_sizes(self):
        coll = {"count": 500, "size": 5_000_000, "totalIndexSize": 1_000_000}
        scaled = compute_collection_scaling(coll, 12_000_000)
        assert scaled["dataSizeProduction"] == pytest.approx(
            (5_000_000 / 500) * 12_000_000
        )
        assert scaled["indexSizeProduction"] == pytest.approx(
            (1_000_000 / 500) * 12_000_000
        )


class TestBuildReport:
    def test_atlas_disk_ram_from_dbstats_not_coll_sum(self):
        db_stats = {
            "objects": 500,
            "avgObjSize": 1000,
            "dataSize": 500_000,
            "storageSize": 400_000,
            "indexSize": 100_000,
        }
        coll_list = [
            {
                "ns": "sizing_example.client_document_history",
                "count": 500,
                "size": 300_000,
                "storageSize": 250_000,
                "totalIndexSize": 60_000,
                "avgObjSize": 600,
            },
            {
                "ns": "sizing_example.client_release_table",
                "count": 500,
                "size": 200_000,
                "storageSize": 150_000,
                "totalIndexSize": 40_000,
                "avgObjSize": 400,
            },
        ]
        sizing_inputs = {
            "collections": {
                "client_document_history": {
                    "anchorTable": "CLIENT_DOCUMENT_HISTORY",
                    "disposition": "anchor",
                    "productionDocumentCount": 12_000_000,
                },
                "client_release_table": {
                    "anchorTable": "CLIENT_RELEASE_TABLE",
                    "disposition": "separate_collection",
                    "productionDocumentCount": 8_000_000,
                },
            },
            "databaseProductionDocumentCount": 20_000_000,
        }
        report = build_report(db_stats, coll_list, 20_000_000, sizing_inputs)

        coll_data_sum = sum(c.get("dataSizeProduction", 0) for c in report["collections"])
        assert coll_data_sum > 0
        assert report["atlas"]["diskRequired"] == pytest.approx(
            report["databaseScaling"]["diskRequired"]
        )
        assert report["atlas"]["diskRequired"] != coll_data_sum
