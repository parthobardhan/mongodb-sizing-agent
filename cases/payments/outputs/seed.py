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

STATUSES = ("AU", "ST", "RJ", "PD")
RAILS = ("ACH", "SWF", "FED", "SEPA")

TEMPLATE_INSTRUCTION = {
    "instructionId": "PAY2026072200000000001",
    "accountId": "ACC00000000000000001",
    "paymentReference": "REF-2026-000001",
    "currencyCode": "USD",
    "totalAmount": 1500.00,
    "instructionStatus": "AU",
    "valueDate": "2026-07-22",
    "createdAt": datetime(2026, 7, 22, 10, 0, 0, tzinfo=timezone.utc),
    "allocationLines": [
        {
            "lineNumber": 1,
            "beneficiaryAccount": "GB29NWBK60161331926819",
            "allocationAmount": 1000.00,
            "costCenter": "CC001",
        },
        {
            "lineNumber": 2,
            "beneficiaryAccount": "DE89370400440532013000",
            "allocationAmount": 500.00,
            "costCenter": "CC002",
        },
    ],
}

TEMPLATE_SETTLEMENT = {
    "instructionId": "PAY2026072200000000001",
    "settlementRail": "ACH",
    "batchSequence": 1,
    "settlementStatus": "ST",
    "settledAt": datetime(2026, 7, 22, 15, 30, 0, tzinfo=timezone.utc),
}


def make_instruction_id(i: int) -> str:
    return f"PAY20260722{str(i).zfill(11)}"


def make_account_id(i: int) -> str:
    return f"ACC{str(i).zfill(17)}"


def randomize_instruction(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["accountId"] = make_account_id(i)
    out["paymentReference"] = f"REF-2026-{i:06d}"
    out["currencyCode"] = rng.choice(["USD", "EUR", "GBP"])
    out["instructionStatus"] = rng.choice(STATUSES)
    out["valueDate"] = (datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))).strftime(
        "%Y-%m-%d"
    )
    out["createdAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))

    n_lines = max(1, int(rng.gauss(EMBEDDED_AVG_CARDINALITY, 1)))
    lines = []
    remaining = round(rng.uniform(500, 5000), 2)
    for ln in range(1, n_lines + 1):
        amount = round(remaining / (n_lines - ln + 1), 2) if ln < n_lines else remaining
        remaining = round(remaining - amount, 2)
        lines.append(
            {
                "lineNumber": ln,
                "beneficiaryAccount": f"IBAN{rng.randint(10**20, 10**21 - 1)}",
                "allocationAmount": amount,
                "costCenter": f"CC{rng.randint(1, 99):03d}",
            }
        )
    out["totalAmount"] = round(sum(line["allocationAmount"] for line in lines), 2)
    out["allocationLines"] = lines
    return out


def randomize_settlement(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["settlementRail"] = rng.choice(RAILS)
    out["batchSequence"] = rng.randint(1, 5)
    out["settlementStatus"] = rng.choice(STATUSES)
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
    print(f"Inserted {RECORDS} documents into {COL_INSTRUCTION} and {COL_SETTLEMENT} on {DB_NAME}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
    args = parser.parse_args(argv)
    seed(args.uri, args.clear)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
