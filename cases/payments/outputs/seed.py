#!/usr/bin/env python3
"""Seed sizing_payment_settlement_platform with 500 docs per top-level collection."""

from __future__ import annotations

import argparse
import copy
import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv()

DB_NAME = "sizing_payment_settlement_platform"
RECORDS = 500
RANDOM_SEED = 20260723
EMBEDDED_AVG_CARDINALITY = 3

COL_INSTRUCTIONS = "payment_instructions"
COL_SETTLEMENT = "settlement_batches"

CURRENCIES = ("USD", "EUR", "GBP", "JPY", "CHF")
INSTRUCTION_STATUSES = ("AU", "ST", "PE", "RJ")
SETTLEMENT_RAILS = ("ACH", "SWF", "FED", "SEPA")
SETTLEMENT_STATUSES = ("ST", "PD", "RJ", "CN")

TEMPLATE_INSTRUCTION = {
    "instructionId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "accountId": "ACC-0000123456",
    "paymentReference": "PMT-2026-000001",
    "currencyCode": "USD",
    "totalAmount": Decimal("15000.0000"),
    "instructionStatus": "AU",
    "valueDate": date(2026, 7, 23),
    "createdAt": datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc),
    "allocationLines": [
        {
            "lineNumber": 1,
            "beneficiaryAccount": "GB82WEST12345698765432",
            "allocationAmount": Decimal("10000.0000"),
            "costCenter": "CC-OPS-01",
        },
        {
            "lineNumber": 2,
            "beneficiaryAccount": "DE89370400440532013000",
            "allocationAmount": Decimal("5000.0000"),
            "costCenter": "CC-OPS-02",
        },
    ],
}

TEMPLATE_SETTLEMENT = {
    "instructionId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "settlementRail": "ACH",
    "batchSequence": 1,
    "settlementStatus": "ST",
    "settledAt": datetime(2026, 7, 23, 15, 30, tzinfo=timezone.utc),
}


def make_instruction_id(i: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"payment-instruction-{i}"))


def randomize_instruction(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["accountId"] = f"ACC-{i:010d}"
    out["paymentReference"] = f"PMT-2026-{i:06d}"
    out["currencyCode"] = rng.choice(CURRENCIES)
    out["instructionStatus"] = rng.choice(INSTRUCTION_STATUSES)
    out["valueDate"] = date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))
    out["createdAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))

    n_lines = max(1, int(rng.gauss(EMBEDDED_AVG_CARDINALITY, 1)))
    lines = []
    remaining = Decimal("0")
    for ln in range(1, n_lines + 1):
        amount = Decimal(str(round(rng.uniform(100, 10000), 4)))
        lines.append(
            {
                "lineNumber": ln,
                "beneficiaryAccount": f"IBAN-{i:06d}-{ln:02d}",
                "allocationAmount": amount,
                "costCenter": f"CC-OPS-{rng.randint(1, 20):02d}",
            }
        )
        remaining += amount
    out["allocationLines"] = lines
    out["totalAmount"] = remaining
    return out


def randomize_settlement(
    doc: dict, i: int, instruction_id: str, rng: random.Random
) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = instruction_id
    out["settlementRail"] = rng.choice(SETTLEMENT_RAILS)
    out["batchSequence"] = rng.randint(1, 5)
    out["settlementStatus"] = rng.choice(SETTLEMENT_STATUSES)
    settled = rng.random() > 0.2
    out["settledAt"] = (
        datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 90))
        if settled
        else None
    )
    return out


def seed(uri: str, clear: bool) -> None:
    rng = random.Random(RANDOM_SEED)
    client = MongoClient(uri)
    db = client[DB_NAME]

    if clear:
        for name in (COL_INSTRUCTIONS, COL_SETTLEMENT):
            db[name].drop()

    instruction_docs = [
        randomize_instruction(TEMPLATE_INSTRUCTION, i, rng) for i in range(1, RECORDS + 1)
    ]
    settlement_docs = [
        randomize_settlement(
            TEMPLATE_SETTLEMENT,
            i,
            instruction_docs[i - 1]["instructionId"],
            rng,
        )
        for i in range(1, RECORDS + 1)
    ]

    db[COL_INSTRUCTIONS].insert_many(instruction_docs)
    db[COL_SETTLEMENT].insert_many(settlement_docs)
    client.close()
    print(
        f"Inserted {RECORDS} documents into {COL_INSTRUCTIONS} and {COL_SETTLEMENT} on {DB_NAME}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
    args = parser.parse_args(argv)
    seed(args.uri, args.clear)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
