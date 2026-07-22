"""Integration tests for migrated ClaimDocumentRepository (requires seeded local Mongo)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pymongo import MongoClient

# Allow importing mongo_repository from the same outputs directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mongo_repository import ClaimDocumentRepository  # noqa: E402

DB_NAME = "sizing_claims_document_history"
SAMPLE_CKEY = "K0000000000000000000001"


@pytest.fixture(scope="module")
def repository() -> ClaimDocumentRepository:
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri)
    db = client[DB_NAME]
    yield ClaimDocumentRepository(db)
    client.close()


def test_find_by_key_returns_document_with_detail_lines(repository: ClaimDocumentRepository):
    doc = repository.find_by_key(SAMPLE_CKEY)
    assert doc is not None
    assert doc["cKey"] == SAMPLE_CKEY
    assert isinstance(doc.get("detailLines"), list)
    assert len(doc["detailLines"]) >= 1


def test_find_detail_lines_ordered(repository: ClaimDocumentRepository):
    lines = repository.find_detail_lines(SAMPLE_CKEY)
    assert len(lines) >= 1
    line_numbers = [line["cLine_Number"] for line in lines]
    assert line_numbers == sorted(line_numbers)
    assert all("cAmount" in line for line in lines)


def test_find_release_composite_key(repository: ClaimDocumentRepository):
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri)
    sample = client[DB_NAME]["client_release_table"].find_one({"cKey": SAMPLE_CKEY})
    client.close()
    assert sample is not None

    release = repository.find_release(
        sample["cKey"],
        sample["cKey_Type"],
        sample["cCopy_Number"],
    )
    assert release is not None
    assert release["cKey"] == sample["cKey"]
    assert release["cKey_Type"] == sample["cKey_Type"]
    assert release["cCopy_Number"] == sample["cCopy_Number"]


def test_count_by_status_positive(repository: ClaimDocumentRepository):
    count = repository.count_by_status("A")
    assert count > 0
