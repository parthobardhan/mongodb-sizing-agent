import pytest

from scripts.sizing_inputs import validate_intake


def test_valid_intake():
    validate_intake(
        {
            "useCaseName": "claims-document-history",
            "queryLatencySlaMs": 50,
            "productionRowCounts": {
                "CLIENT_DOCUMENT_HISTORY": 12_000_000,
                "CLIENT_RELEASE_TABLE": 8_000_000,
            },
            "dataModelingNotes": "Detail lines read with parent claim.",
            "assumptions": [],
            "discountPercent": None,
            "supportUpliftPercent": None,
        }
    )


def test_intake_without_optional_sizing_fields():
    validate_intake(
        {
            "useCaseName": "claims-document-history",
            "queryLatencySlaMs": 50,
            "assumptions": [],
        }
    )


def test_missing_use_case_fails():
    with pytest.raises(Exception):
        validate_intake({"queryLatencySlaMs": 50})
