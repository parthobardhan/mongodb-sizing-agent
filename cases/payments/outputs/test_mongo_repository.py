"""Integration tests for migrated PaymentSettlementRepository (requires seeded local Mongo)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mongo_repository import PaymentSettlementRepository  # noqa: E402

DB_NAME = "sizing_payment_settlement_platform"
SAMPLE_INSTRUCTION_ID = "P0000000000000000000001"


@pytest.fixture(scope="module")
def repository() -> PaymentSettlementRepository:
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri)
    db = client[DB_NAME]
    yield PaymentSettlementRepository(db)
    client.close()


def test_find_by_instruction_id_returns_document_with_allocation_lines(
    repository: PaymentSettlementRepository,
):
    doc = repository.find_by_instruction_id(SAMPLE_INSTRUCTION_ID)
    assert doc is not None
    assert doc["instructionId"] == SAMPLE_INSTRUCTION_ID
    assert isinstance(doc.get("allocationLines"), list)
    assert len(doc["allocationLines"]) >= 1


def test_find_allocation_lines_ordered(repository: PaymentSettlementRepository):
    lines = repository.find_allocation_lines(SAMPLE_INSTRUCTION_ID)
    assert len(lines) >= 1
    line_numbers = [line["lineNumber"] for line in lines]
    assert line_numbers == sorted(line_numbers)
    assert all("allocationAmount" in line for line in lines)


def test_find_settlement_batch_composite_key(repository: PaymentSettlementRepository):
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri)
    sample = client[DB_NAME]["settlement_batch"].find_one(
        {"instructionId": SAMPLE_INSTRUCTION_ID}
    )
    client.close()
    assert sample is not None

    batch = repository.find_settlement_batch(
        sample["instructionId"],
        sample["settlementRail"],
        sample["batchSequence"],
    )
    assert batch is not None
    assert batch["instructionId"] == sample["instructionId"]
    assert batch["settlementRail"] == sample["settlementRail"]
    assert batch["batchSequence"] == sample["batchSequence"]


def test_count_by_instruction_status_positive(repository: PaymentSettlementRepository):
    count = repository.count_by_instruction_status("AU")
    assert count > 0
