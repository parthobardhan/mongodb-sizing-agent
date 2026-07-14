"""Render sizing-report.md from sizing-report.json structure."""

from __future__ import annotations

from typing import Any


def _fmt_bytes(n: float | int | None) -> str:
    if n is None:
        return "—"
    val = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(val) < 1024 or unit == "TB":
            return f"{val:,.2f} {unit}"
        val /= 1024
    return f"{val:,.2f} TB"


def render_sizing_report_md(report: dict[str, Any]) -> str:
    lines = ["# MongoDB Sizing Report", ""]
    db = report.get("dbStats", {})
    lines.append("## Sample database stats (dbStats)")
    lines.append("")
    lines.append(f"- Objects (sample): **{db.get('objects', '—')}**")
    lines.append(f"- Avg object size: **{_fmt_bytes(db.get('avgObjSize'))}**")
    lines.append(f"- Data size: **{_fmt_bytes(db.get('dataSize'))}**")
    lines.append(f"- Storage size: **{_fmt_bytes(db.get('storageSize'))}**")
    lines.append(f"- Index size: **{_fmt_bytes(db.get('indexSize'))}**")
    lines.append("")

    lines.append("## Per-collection (collStats → production scale)")
    lines.append("")
    lines.append(
        "| Collection | Sample count | Prod docs | Data (prod) | Index (prod) |"
    )
    lines.append("|------------|--------------|-----------|-------------|--------------|")

    for col in report.get("collections", []):
        cs = col.get("collStats", {})
        lines.append(
            f"| {col.get('name', '—')} "
            f"| {cs.get('count', '—')} "
            f"| {col.get('productionDocumentCount', '—')} "
            f"| {_fmt_bytes(col.get('dataSizeProduction'))} "
            f"| {_fmt_bytes(col.get('indexSizeProduction'))} |"
        )
    lines.append("")

    ds = report.get("databaseScaling", {})
    atlas = report.get("atlas", {})
    prod = report.get("databaseProductionDocumentCount", "—")
    lines.append("## Atlas sizing (from dbStats scaling)")
    lines.append("")
    lines.append(f"- Production document count (database): **{prod}**")
    if ds.get("compression") is not None:
        lines.append(f"- Compression ratio: **{ds['compression']:.4f}**")
    basis = ds.get("sizingBasis")
    if basis:
        lines.append(f"- Sizing basis: **{basis}**")
    lines.append(f"- Data size (production): **{_fmt_bytes(ds.get('dataSizeProduction'))}**")
    lines.append(f"- Storage size (production): **{_fmt_bytes(ds.get('storageSizeProduction'))}**")
    lines.append(f"- Index size (production): **{_fmt_bytes(ds.get('indexSizeProduction'))}**")
    lines.append(f"- RAM usage estimate (index × 1.5): **{_fmt_bytes(ds.get('ramUsage'))}**")
    lines.append(f"- **Disk required** (storage / 0.75): **{_fmt_bytes(atlas.get('diskRequired'))}**")
    lines.append(f"- **RAM required**: **{_fmt_bytes(atlas.get('ramRequired'))}**")
    if ds.get("warning"):
        lines.append(f"- Warning: {ds['warning']}")
    lines.append("")
    lines.append(
        "_Per-collection rows are for detail; Disk/RAM above use database-level dbStats only._"
    )
    lines.append("")
    return "\n".join(lines)
