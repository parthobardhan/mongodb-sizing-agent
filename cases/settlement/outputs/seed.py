#!/usr/bin/env python3
"""Seed sizing_payment_settlement_platform with 500 docs per top-level collection."""

from __future__ import annotations

import argparse
import copy
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv()

DB_NAME = "sizing_payment_settlement_platform"
RECORDS = 500
RANDOM_SEED = 20260724
EMBEDDED_AVG_CARDINALITY = 3

COL_INSTRUCTION = "payment_instruction"
COL_BATCH = "settlement_batch"

CURRENCIES = ("USD", "EUR", "GBP")
INSTRUCTION_STATUSES = ("AU", "ST", "PD", "RJ")
SETTLEMENT_RAILS = ("ACH", "WIR", "SWF")
SETTLEMENT_STATUSES = ("ST", "PE", "FA")

TEMPLATE_INSTRUCTION = {
    "instructionId": "PI-0000000000000000000001",
    "accountId": "ACC-0000000001",
    "paymentReference": "PAY-REF-2026-000001",
    "currencyCode": "USD",
    "totalAmount": 15000.0,
    "instructionStatus": "AU",
    "valueDate": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
    "createdAt": datetime.now(timezone.utc),
    "allocationLines": [
        {
            "lineNumber": 1,
            "beneficiaryAccount": "BNF-00000000000000000001",
            "allocationAmount": 10000.0,
            "costCenter": "CC-OPS-01",
        }
    ],
}

TEMPLATE_BATCH = {
    "instructionId": "PI-0000000000000000000001",
    "settlementRail": "ACH",
    "batchSequence": 1,
    "settlementStatus": "ST",
    "settledAt": datetime.now(timezone.utc),
}


def make_instruction_id(i: int) -> str:
    return f"PI-{str(i).zfill(22)}"


def randomize_instruction(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["accountId"] = f"ACC-{str(i).zfill(10)}"
    out["paymentReference"] = f"PAY-REF-2026-{i:06d}"
    out["currencyCode"] = rng.choice(CURRENCIES)
    out["instructionStatus"] = rng.choice(INSTRUCTION_STATUSES)
    out["valueDate"] = (
        datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    out["createdAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))

    n_lines = max(1, int(rng.gauss(EMBEDDED_AVG_CARDINALITY, 1)))
    lines = []
    remaining = 10000.0
    for ln in range(1, n_lines + 1):
        if ln == n_lines:
            amount = round(remaining, 4)
        else:
            amount = round(rng.uniform(100, remaining / 2), 4)
            remaining -= amount
        lines.append(
            {
                "lineNumber": ln,
                "beneficiaryAccount": f"BNF-{str(i * 100 + ln).zfill(20)}",
                "allocationAmount": amount,
                "costCenter": f"CC-OPS-{ln:02d}",
            }
        )
    out["allocationLines"] = lines
    out["totalAmount"] = round(sum(line["allocationAmount"] for line in lines), 4)
    return out


def randomize_batch(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["settlementRail"] = rng.choice(SETTLEMENT_RAILS)
    out["batchSequence"] = rng.randint(1, 5)
    out["settlementStatus"] = rng.choice(SETTLEMENT_STATUSES)
    out["settledAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 180))
    return out


def seed(uri: str, clear: bool) -> None:
    rng = random.Random(RANDOM_SEED)
    client = MongoClient(uri)
    db = client[DB_NAME]

    if clear:
        for name in (COL_INSTRUCTION, COL_BATCH):
            db[name].drop()

    instruction_docs = [
        randomize_instruction(TEMPLATE_INSTRUCTION, i, rng) for i in range(1, RECORDS + 1)
    ]
    batch_docs = [randomize_batch(TEMPLATE_BATCH, i, rng) for i in range(1, RECORDS + 1)]

    db[COL_INSTRUCTION].insert_many(instruction_docs)
    db[COL_BATCH].insert_many(batch_docs)
    client.close()
    print(f"Inserted {RECORDS} documents into {COL_INSTRUCTION} and {COL_BATCH} on {DB_NAME}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
    args = parser.parse_args(argv)
    seed(args.uri, args.clear)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
