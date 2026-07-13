import pytest

from scripts.sizing_inputs import derive_embedded_cardinality, validate_sizing_inputs


def test_derive_cardinality_1000_5000():
    result = derive_embedded_cardinality(1000, 5000)
    assert result["avgCardinality"] == 5.0
    assert result["ratioLabel"] == "1000:5000"
    assert result["derivedFrom"]["method"].startswith("child")


def test_validate_sizing_inputs_minimal():
    validate_sizing_inputs(
        {
            "collections": {
                "orders": {
                    "anchorTable": "ORDERS",
                    "disposition": "anchor",
                    "productionDocumentCount": 1000,
                }
            },
            "databaseProductionDocumentCount": 1000,
        }
    )


def test_derive_requires_positive_parent():
    with pytest.raises(ValueError):
        derive_embedded_cardinality(0, 5000)
