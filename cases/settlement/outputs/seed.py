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

COL_PAYMENT = "payment_instruction"
COL_SETTLEMENT = "settlement_batch"

STATUSES = ("AU", "PD", "ST", "CA")
RAILS = ("ACH", "WIR", "RTP", "CHK")

TEMPLATE_PAYMENT = {
    "instructionId": "P0000000000000000000001",
    "accountId": "ACC00000000000000001",
    "paymentReference": "REF-000001",
    "currencyCode": "USD",
    "totalAmount": 1500.0,
    "instructionStatus": "AU",
    "valueDate": datetime(2026, 7, 22, tzinfo=timezone.utc),
    "createdAt": datetime.now(timezone.utc),
    "allocationLines": [
        {
            "lineNumber": 1,
            "beneficiaryAccount": "GB29NWBK60161331926819",
            "allocationAmount": 1500.0,
            "costCenter": "CC001",
        }
    ],
}

TEMPLATE_SETTLEMENT = {
    "instructionId": "P0000000000000000000001",
    "settlementRail": "ACH",
    "batchSequence": 1,
    "settlementStatus": "ST",
    "settledAt": datetime.now(timezone.utc),
}


def make_instruction_id(i: int) -> str:
    return f"P{str(i).zfill(22)}"


def make_account_id(i: int) -> str:
    return f"ACC{str(i).zfill(17)}"


def randomize_payment(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["accountId"] = make_account_id(i)
    out["paymentReference"] = f"REF-{i:06d}"
    out["currencyCode"] = rng.choice(("USD", "EUR", "GBP", "JPY"))
    out["instructionStatus"] = "AU" if i % 5 != 0 else rng.choice(STATUSES)
    out["valueDate"] = datetime(2026, 7, 22, tzinfo=timezone.utc) - timedelta(
        days=rng.randint(0, 90)
    )
    out["createdAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365))
    n_lines = max(1, int(rng.gauss(EMBEDDED_AVG_CARDINALITY, 0.75)))
    lines = []
    remaining = round(rng.uniform(100, 10000), 2)
    for ln in range(1, n_lines + 1):
        if ln == n_lines:
            amount = remaining
        else:
            amount = round(remaining / (n_lines - ln + 1) * rng.uniform(0.4, 0.8), 2)
            remaining = round(remaining - amount, 2)
        lines.append(
            {
                "lineNumber": ln,
                "beneficiaryAccount": f"BEN{rng.randint(10**15, 10**16 - 1)}",
                "allocationAmount": amount,
                "costCenter": f"CC{rng.randint(1, 99):03d}",
            }
        )
    out["allocationLines"] = lines
    out["totalAmount"] = round(sum(line["allocationAmount"] for line in lines), 2)
    return out


def randomize_settlement(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["instructionId"] = make_instruction_id(i)
    out["settlementRail"] = rng.choice(RAILS)
    out["batchSequence"] = rng.randint(1, 5)
    out["settlementStatus"] = rng.choice(("ST", "PD", "FL"))
    out["settledAt"] = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 180))
    return out


def seed(uri: str, clear: bool) -> None:
    rng = random.Random(RANDOM_SEED)
    client = MongoClient(uri)
    db = client[DB_NAME]

    if clear:
        for name in (COL_PAYMENT, COL_SETTLEMENT):
            db[name].drop()

    payment_docs = [randomize_payment(TEMPLATE_PAYMENT, i, rng) for i in range(1, RECORDS + 1)]
    settlement_docs = [
        randomize_settlement(TEMPLATE_SETTLEMENT, i, rng) for i in range(1, RECORDS + 1)
    ]

    db[COL_PAYMENT].insert_many(payment_docs)
    db[COL_SETTLEMENT].insert_many(settlement_docs)
    client.close()
    print(f"Inserted {RECORDS} documents into {COL_PAYMENT} and {COL_SETTLEMENT} on {DB_NAME}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
    args = parser.parse_args(argv)
    seed(args.uri, args.clear)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
