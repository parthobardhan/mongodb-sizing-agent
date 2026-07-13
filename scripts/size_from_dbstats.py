#!/usr/bin/env python3
"""Compute MongoDB sizing from dbStats + per-collection collStats."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from pymongo import MongoClient

# Allow running as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.sizing_inputs import database_production_document_count, load_sizing_inputs
from scripts.report_render import render_sizing_report_md


def compute_dbstats_scaling(
    db_stats: dict[str, Any],
    production_count: int,
) -> dict[str, Any]:
    """Steps 4–5: database-level Atlas inputs from dbStats only."""
    objects = db_stats.get("objects") or 0
    data_size = db_stats.get("dataSize") or 0
    storage_size = db_stats.get("storageSize") or 0
    index_size = db_stats.get("indexSize") or 0
    avg_obj_size = db_stats.get("avgObjSize") or 0

    compression = None
    if data_size > 0:
        compression = 1 - (storage_size / data_size)

    if objects <= 0:
        return {
            "compression": compression,
            "dataSizeProduction": 0,
            "storageSizeProduction": 0,
            "indexSizeProduction": 0,
            "ramUsage": 0,
            "diskRequired": 0,
            "ramRequired": 0,
            "warning": "dbStats.objects is zero; cannot scale",
        }

    data_size_production = avg_obj_size * production_count
    storage_size_production = (storage_size / objects) * production_count
    index_size_production = (index_size / objects) * production_count
    ram_usage = index_size_production * 1.5
    disk_required = storage_size_production / 0.75
    ram_required = ram_usage

    return {
        "compression": compression,
        "dataSizeProduction": data_size_production,
        "storageSizeProduction": storage_size_production,
        "indexSizeProduction": index_size_production,
        "ramUsage": ram_usage,
        "diskRequired": disk_required,
        "ramRequired": ram_required,
    }


def compute_collection_scaling(
    coll_stats: dict[str, Any],
    production_document_count: int,
) -> dict[str, Any]:
    """Step 3: per-collection production data/index sizes."""
    count = coll_stats.get("count") or 0
    size = coll_stats.get("size") or 0
    total_index_size = coll_stats.get("totalIndexSize") or 0

    if count <= 0:
        return {
            "dataSizeProduction": 0,
            "indexSizeProduction": 0,
            "warning": "collStats.count is zero; cannot scale",
        }

    return {
        "dataSizeProduction": (size / count) * production_document_count,
        "indexSizeProduction": (total_index_size / count) * production_document_count,
    }


def build_report(
    db_stats: dict[str, Any],
    coll_stats_list: list[dict[str, Any]],
    production_count: int,
    sizing_inputs: dict[str, Any],
) -> dict[str, Any]:
    collections_meta = sizing_inputs.get("collections", {})
    collections_out: list[dict[str, Any]] = []

    for cs in coll_stats_list:
        ns = cs.get("ns", "")
        name = ns.split(".", 1)[-1] if "." in ns else ns
        if name.startswith("system."):
            continue

        meta = collections_meta.get(name, {})
        prod_count = meta.get("productionDocumentCount")
        entry: dict[str, Any] = {
            "name": name,
            "ns": ns,
            "collStats": {
                "count": cs.get("count"),
                "avgObjSize": cs.get("avgObjSize"),
                "size": cs.get("size"),
                "storageSize": cs.get("storageSize"),
                "totalIndexSize": cs.get("totalIndexSize"),
            },
            "anchorTable": meta.get("anchorTable"),
            "disposition": meta.get("disposition"),
            "productionDocumentCount": prod_count,
        }

        if prod_count is not None:
            scaled = compute_collection_scaling(cs, int(prod_count))
            entry.update(scaled)
        else:
            entry["warning"] = "productionDocumentCount missing in sizing_inputs"

        collections_out.append(entry)

    database_scaling = compute_dbstats_scaling(db_stats, production_count)

    return {
        "dbStats": db_stats,
        "collections": collections_out,
        "databaseProductionDocumentCount": production_count,
        "databaseScaling": database_scaling,
        "atlas": {
            "diskRequired": database_scaling["diskRequired"],
            "ramRequired": database_scaling["ramRequired"],
        },
    }


_WT_MIN_PAGE_BYTES = 4096
_MIN_LOGICAL_SIZE_FOR_PAGE_CHECK = 8192


def _collection_name(coll_stats: dict[str, Any]) -> str:
    ns = coll_stats.get("ns", "")
    return ns.split(".", 1)[-1] if "." in ns else ns


def _stats_fingerprint(
    db_stats: dict[str, Any],
    coll_stats_list: list[dict[str, Any]],
) -> tuple[Any, ...]:
    coll_part = tuple(
        sorted(
            (
                _collection_name(cs),
                cs.get("storageSize") or 0,
                cs.get("totalIndexSize") or 0,
            )
            for cs in coll_stats_list
            if not _collection_name(cs).startswith("system.")
        )
    )
    return (
        db_stats.get("storageSize") or 0,
        db_stats.get("indexSize") or 0,
        coll_part,
    )


def _has_minimum_page_only(coll_stats_list: list[dict[str, Any]]) -> bool:
    """True when a non-empty collection still reports only one WiredTiger page."""
    for cs in coll_stats_list:
        name = _collection_name(cs)
        if name.startswith("system."):
            continue
        count = cs.get("count") or 0
        size = cs.get("size") or 0
        storage = cs.get("storageSize") or 0
        if count > 0 and size > _MIN_LOGICAL_SIZE_FOR_PAGE_CHECK and storage <= _WT_MIN_PAGE_BYTES:
            return True
    return False


def flush_storage_stats(client: MongoClient) -> None:
    """Force WiredTiger to flush so dbStats/collStats reflect on-disk allocation."""
    admin = client.admin
    try:
        admin.command("checkpoint")
    except Exception:
        pass
    admin.command("fsync", lock=False)


def _read_stats(db) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    db_stats = db.command("dbStats")
    coll_stats_list: list[dict[str, Any]] = []
    for name in db.list_collection_names():
        if name.startswith("system."):
            continue
        coll_stats_list.append(db.command("collStats", name))
    return db_stats, coll_stats_list


def collect_stats(uri: str, db_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    client = MongoClient(uri)
    try:
        return _read_stats(client[db_name])
    finally:
        client.close()


def wait_for_stable_stats(
    uri: str,
    db_name: str,
    *,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 1.0,
    stable_polls: int = 2,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Flush and poll until dbStats/collStats stop changing."""
    client = MongoClient(uri)
    try:
        db = client[db_name]
        deadline = time.monotonic() + timeout_sec
        stable_seen = 0
        last_fingerprint: tuple[Any, ...] | None = None
        db_stats: dict[str, Any]
        coll_stats_list: list[dict[str, Any]]

        while True:
            flush_storage_stats(client)
            db_stats, coll_stats_list = _read_stats(db)
            fingerprint = _stats_fingerprint(db_stats, coll_stats_list)
            pages_only = _has_minimum_page_only(coll_stats_list)

            if (
                not pages_only
                and last_fingerprint is not None
                and fingerprint == last_fingerprint
            ):
                stable_seen += 1
                if stable_seen >= stable_polls:
                    print(
                        f"Storage stats stable after {stable_polls} matching poll(s)",
                        file=sys.stderr,
                    )
                    return db_stats, coll_stats_list
            else:
                stable_seen = 0

            last_fingerprint = fingerprint
            if time.monotonic() >= deadline:
                print(
                    "warning: storage stats did not fully stabilize before timeout; "
                    "using latest checkpointed values",
                    file=sys.stderr,
                )
                return db_stats, coll_stats_list

            time.sleep(poll_interval_sec)
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Size MongoDB from dbStats/collStats")
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", required=True)
    parser.add_argument("--production-count", type=int)
    parser.add_argument("--sizing-inputs-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Collect stats immediately without waiting for stable storageSize",
    )
    parser.add_argument(
        "--wait-timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for stable storage stats (default: 30)",
    )
    args = parser.parse_args(argv)

    sizing_inputs: dict[str, Any] = {}
    if args.sizing_inputs_file:
        sizing_inputs = load_sizing_inputs(args.sizing_inputs_file)

    production_count = args.production_count
    if production_count is None and sizing_inputs:
        production_count = database_production_document_count(sizing_inputs)
    if production_count is None:
        print("error: --production-count or sizing_inputs with counts required", file=sys.stderr)
        return 1

    if args.no_wait:
        db_stats, coll_stats_list = collect_stats(args.uri, args.db)
    else:
        db_stats, coll_stats_list = wait_for_stable_stats(
            args.uri,
            args.db,
            timeout_sec=args.wait_timeout,
        )
    report = build_report(db_stats, coll_stats_list, production_count, sizing_inputs)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    md_path = args.md_out or args.out.with_suffix(".md")
    md_path.write_text(render_sizing_report_md(report), encoding="utf-8")
    print(f"Wrote {args.out} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
