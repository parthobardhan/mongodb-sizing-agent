from scripts.report_render import render_sizing_report_md


def test_report_has_required_sections():
    report = {
        "dbStats": {"objects": 500, "avgObjSize": 100, "dataSize": 50000, "storageSize": 40000, "indexSize": 10000},
        "collections": [
            {
                "name": "client_document_history",
                "collStats": {"count": 500},
                "productionDocumentCount": 12_000_000,
                "dataSizeProduction": 1e9,
                "indexSizeProduction": 2e8,
            }
        ],
        "databaseProductionDocumentCount": 20_000_000,
        "databaseScaling": {
            "compression": 0.2,
            "dataSizeProduction": 2e9,
            "storageSizeProduction": 1.6e9,
            "indexSizeProduction": 4e8,
            "ramUsage": 6e8,
            "diskRequired": 2.133e9,
            "ramRequired": 6e8,
            "sizingBasis": "measured-storage",
        },
        "atlas": {"diskRequired": 2.133e9, "ramRequired": 6e8},
    }
    md = render_sizing_report_md(report)
    assert "# MongoDB Sizing Report" in md
    assert "## Per-collection" in md
    assert "## Atlas sizing" in md
    assert "client_document_history" in md
    assert "Disk required" in md
    assert "Sizing basis: **measured-storage**" in md


def test_report_includes_data_size_floor_basis_and_warning():
    report = {
        "dbStats": {"objects": 500, "dataSize": 290000, "storageSize": 4096},
        "collections": [],
        "databaseProductionDocumentCount": 20_000_000,
        "databaseScaling": {
            "compression": 0.98,
            "dataSizeProduction": 5.54e9,
            "storageSizeProduction": 2.77e9,
            "indexSizeProduction": 1e9,
            "ramUsage": 1.5e9,
            "diskRequired": 3.69e9,
            "ramRequired": 1.5e9,
            "sizingBasis": "data-size-floor",
            "warning": "dbStats.storageSize looks like a tiny WiredTiger sample",
        },
        "atlas": {"diskRequired": 3.69e9, "ramRequired": 1.5e9},
    }
    md = render_sizing_report_md(report)
    assert "Sizing basis: **data-size-floor**" in md
    assert "Warning: dbStats.storageSize looks like a tiny WiredTiger sample" in md
