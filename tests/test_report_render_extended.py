from scripts.report_render import render_sizing_report_md


def test_report_includes_warnings_when_present():
    report = {
        "dbStats": {"objects": 0, "dataSize": 0, "storageSize": 0, "indexSize": 0},
        "collections": [
            {
                "name": "orders",
                "collStats": {"count": 0},
                "productionDocumentCount": None,
                "warning": "productionDocumentCount missing in sizing_inputs",
            }
        ],
        "databaseProductionDocumentCount": 1000,
        "databaseScaling": {
            "dataSizeProduction": 0,
            "storageSizeProduction": 0,
            "indexSizeProduction": 0,
            "ramUsage": 0,
            "diskRequired": 0,
            "ramRequired": 0,
        },
        "atlas": {"diskRequired": 0, "ramRequired": 0},
    }
    md = render_sizing_report_md(report)
    assert "orders" in md
    assert "# MongoDB Sizing Report" in md


def test_report_handles_empty_collections():
    report = {
        "dbStats": {"objects": 0},
        "collections": [],
        "databaseProductionDocumentCount": 0,
        "databaseScaling": {
            "dataSizeProduction": 0,
            "storageSizeProduction": 0,
            "indexSizeProduction": 0,
            "ramUsage": 0,
            "diskRequired": 0,
            "ramRequired": 0,
        },
        "atlas": {"diskRequired": 0, "ramRequired": 0},
    }
    md = render_sizing_report_md(report)
    assert "## Per-collection" in md
    assert "## Atlas sizing" in md
