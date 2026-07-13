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
        },
        "atlas": {"diskRequired": 2.133e9, "ramRequired": 6e8},
    }
    md = render_sizing_report_md(report)
    assert "# MongoDB Sizing Report" in md
    assert "## Per-collection" in md
    assert "## Atlas sizing" in md
    assert "client_document_history" in md
    assert "Disk required" in md
