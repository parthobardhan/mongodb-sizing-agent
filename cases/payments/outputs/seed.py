#!/usr/bin/env python3
"""Seed sizing_payment_settlement_platform with 500 docs per top-level collection."""

from __future__ import annotations

import argparse
import copy
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv()

DB_NAME = "sizing_payment_settlement_platform"
RECORDS = 500
RANDOM_SEED = 20260723
EMBEDDED_AVG_CARDINALITY = 3

COL_INSTRUCTION = "payment_instruction"
COL_SETTLEMENT = "settlement_batch"

TEMPLATE_INSTRUCTION = {
    "instructionId": "550e8400-e29b-41d4-a716-446655440000",
    "accountId": "ACCT-0000123456",
    "paymentReference": "PAY-2026-000001",
    "currencyCode": "USD",
    "totalAmount": 15000.0000,
    "instructionStatus": "AU",
    "valueDate": datetime(2026, 7, 23, tzinfo=timezone.utc),
    "createdAt": datetime(2026, 7, 23, 8, 0, 0, tzinfo=timezone.utc),
    "allocationLines": [
        {
            "lineNumber": 1,
            "beneficiaryAccount": "GB82WEST12345698765432",
            "allocationAmount": 10000.0000,
            "costCenter": "CC-OPS-01",
        },
        {
            "lineNumber": 2,
            "beneficiaryAccount": "DE89370400440532013000",
            "allocationAmount": 5000.0000,
            "costCenter": "CC-OPS-02",
        },
    ],
}

TEMPLATE_SETTLEMENT = {
    "instructionId": "550e8400-e29b-41d4-a716-446655440000",
    "settlementRail": "ACH",
    "batchSequence": 1,
    "settlementStatus": "ST",
    "settledAt": datetime(2026, 7, 23, 10, 30, 0, tzinfo=timezone.utc),
}

SETTLEMENT_RAILS = ("ACH", "SWF", "FED")
INSTRUCTION_STATUSES = ("AU", "ST", "PD", "RJ")
CURRENCIES = ("USD", "EUR", "GBP")


def make_instruction_id(i: int) -> str:
    return f"550e8400-e29b-41d4-a716-{str(i).zfill(12)}"


def randomize_instruction(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["accountId"] = f"ACCT-{i:010d}"
    out["paymentReference"] = f"PAY-2026-{i:06d}"
    out["currencyCode"] = rng.choice(CURRENCIES)
    out["instructionStatus"] = rng.choice(INSTRUCTION_STATUSES)
    out["valueDate"] = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 200))
    out["createdAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))
    lines = []
    n_lines = max(1, int(rng.gauss(EMBEDDED_AVG_CARDINALITY, 1)))
    total = 0.0
    for ln in range(1, n_lines + 1):
        amount = round(rng.uniform(100, 10000), 4)
        total += amount
        lines.append(
            {
                "lineNumber": ln,
                "beneficiaryAccount": f"{'GB' if rng.random() > 0.5 else 'DE'}{rng.randint(10**20, 10**22 - 1)}",
                "allocationAmount": amount,
                "costCenter": f"CC-OPS-{ln:02d}",
            }
        )
    out["allocationLines"] = lines
    out["totalAmount"] = total
    return out


def randomize_settlement(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["settlementRail"] = rng.choice(SETTLEMENT_RAILS)
    out["batchSequence"] = rng.randint(1, 5)
    out["settlementStatus"] = rng.choice(("ST", "PD", "FL"))
    out["settledAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 180))
    return out


def seed(uri: str, clear: bool) -> None:
    rng = random.Random(RANDOM_SEED)
    client = MongoClient(uri)
    db = client[DB_NAME]

    if clear:
        for name in (COL_INSTRUCTION, COL_SETTLEMENT):
            db[name].drop()

    instruction_docs = [
        randomize_instruction(TEMPLATE_INSTRUCTION, i, rng) for i in range(1, RECORDS + 1)
    ]
    settlement_docs = [
        randomize_settlement(TEMPLATE_SETTLEMENT, i, rng) for i in range(1, RECORDS + 1)
    ]

    db[COL_INSTRUCTION].insert_many(instruction_docs)
    db[COL_SETTLEMENT].insert_many(settlement_docs)
    client.close()
    print(
        f"Inserted {RECORDS} documents into {COL_INSTRUCTION} and {COL_SETTLEMENT} on {DB_NAME}"
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
