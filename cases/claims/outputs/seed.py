#!/usr/bin/env python3
"""Seed sizing_claims_document_history with 500 documents per collection."""

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

DB_NAME = "sizing_claims_document_history"
RECORDS = 500
RANDOM_SEED = 20260722
EMBEDDED_AVG_CARDINALITY = 5
BASE_DATETIME = datetime(2026, 7, 22, tzinfo=timezone.utc)

COL_HISTORY = "client_document_history"
COL_RELEASE = "client_release_table"

TEMPLATE_HISTORY = {
    "cKey": "K0000000000000000000001",
    "cSuper_Key": None,
    "cClaim_Number": "CLM-000001",
    "cStatus": "A",
    "cCreated_Date": BASE_DATETIME,
    "detailLines": [
        {
            "cClaim_Number": "CLM-000001",
            "cLine_Number": 1,
            "cAmount": 100.0,
        }
    ],
}

TEMPLATE_RELEASE = {
    "cKey": "K0000000000000000000001",
    "cKey_Type": "01",
    "cCopy_Number": 1,
    "cRelease_Date": BASE_DATETIME,
}


def make_ckey(i: int) -> str:
    return f"K{str(i).zfill(22)}"


def randomize_history(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["cKey"] = make_ckey(i)
    out["cClaim_Number"] = f"CLM-{i:06d}"
    out["cCreated_Date"] = BASE_DATETIME - timedelta(days=rng.randint(0, 365))
    out["detailLines"] = [
        {
            "cClaim_Number": out["cClaim_Number"],
            "cLine_Number": line_number,
            "cAmount": round(rng.uniform(10, 5000), 2),
        }
        for line_number in range(1, EMBEDDED_AVG_CARDINALITY + 1)
    ]
    return out


def randomize_release(doc: dict, i: int, rng: random.Random) -> dict:
    out = copy.deepcopy(doc)
    out["cKey"] = make_ckey(i)
    out["cKey_Type"] = f"{rng.randint(1, 99):02d}"
    out["cCopy_Number"] = rng.randint(1, 5)
    out["cRelease_Date"] = BASE_DATETIME - timedelta(days=rng.randint(0, 180))
    return out


def seed(uri: str, clear: bool) -> None:
    rng = random.Random(RANDOM_SEED)
    client = MongoClient(uri)
    db = client[DB_NAME]
    try:
        if clear:
            for collection_name in (COL_HISTORY, COL_RELEASE):
                db[collection_name].drop()

        history_docs = [
            randomize_history(TEMPLATE_HISTORY, i, rng)
            for i in range(1, RECORDS + 1)
        ]
        release_docs = [
            randomize_release(TEMPLATE_RELEASE, i, rng)
            for i in range(1, RECORDS + 1)
        ]
        db[COL_HISTORY].insert_many(history_docs)
        db[COL_RELEASE].insert_many(release_docs)
    finally:
        client.close()

    print(
        f"Inserted {RECORDS} documents into {COL_HISTORY} and "
        f"{COL_RELEASE} on {DB_NAME}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    parser.add_argument(
        "--uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    )
    args = parser.parse_args(argv)
    seed(args.uri, args.clear)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
