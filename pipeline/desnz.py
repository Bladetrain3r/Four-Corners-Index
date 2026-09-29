"""DESNZ Quarterly Energy Prices, international tables 5.6.2 (household) and 5.4.2 (non-household), United Kingdom column. OGL v3.0.

Both tables use Eurostat's consumption bands (household Medium 2,500-4,999 kWh/yr = Eurostat DC; non-household Medium
2,000-19,999 MWh/yr = Eurostat ID), half-yearly, in pence per kWh. Only rows on the current (2015) methodology are kept:
earlier segments are not comparable. The live source is an XLSX workbook; the committed fixtures are CSV extractions of the same sheets.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from pipeline import xlsx
from pipeline.common import SourceError, check_gap_share, gap, sha256_hex, validate_point

SOURCE = "desnz"
COLUMN = "United Kingdom"
METHODOLOGY = "2015"
TABLES = {  # table -> (buyer_type, band text that must appear, sheet name prefix)
    "5.6.2": ("household", "2,500 - 4,999 kWh", "5.6.2 (Medium "),
    "5.4.2": ("industrial", "2,000 - 19,999 MWh", "5.4.2 (Medium "),
}
LEVELS = {"incl tax": "incl_tax", "excl tax": "excl_tax"}
_YEAR = re.compile(r"^(\d{4})\s*r?$")


def _sheets(raw: bytes, table: str, kind: str) -> dict[str, list[list[str]]]:
    prefix = TABLES[table][2]
    if kind == "fixture":
        found = xlsx.split_csv_sheets(raw)
    else:
        found = {f"{prefix}{lv})": xlsx.read_xlsx_sheet(raw, f"{prefix}{lv})", SOURCE) for lv in LEVELS}
    out = {name: g for name, g in found.items() if name.startswith(prefix)}
    missing = [f"{prefix}{lv})" for lv in LEVELS if f"{prefix}{lv})" not in out]
    if missing:
        raise SourceError(SOURCE, f"table {table}: sheets {missing} not found (renumbered or renamed?)")
    return out


def _number(text: str, table: str, where: str) -> Decimal:
    t = text.strip()
    if t.endswith("r"):  # revised marker
        t = t[:-1].strip()
    try:
        d = Decimal(t)
    except InvalidOperation as exc:
        raise SourceError(SOURCE, f"table {table}: {where}: value {text!r} is not numeric") from exc
    if not d.is_finite():
        raise SourceError(SOURCE, f"table {table}: {where}: value not finite")
    return d


def _period(year: int, label: str, table: str) -> tuple[date, date]:
    lab = label.strip().lower()
    if lab.startswith("jan"):
        return date(year, 1, 1), date(year, 6, 30)
    if lab.startswith("jul"):
        return date(year, 7, 1), date(year, 12, 31)
    raise SourceError(SOURCE, f"table {table}: unrecognised period label {label!r}")


def parse(raw: bytes, retrieved_at: str, table: str, kind: str = "live", confidence: str = "primary",
          gaps: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if table not in TABLES:
        raise SourceError(SOURCE, f"unknown table {table!r}")
    buyer, band, _ = TABLES[table]
    digest = sha256_hex(raw)
    out: list[dict[str, Any]] = []
    for name, grid in sorted(_sheets(raw, table, kind).items()):
        level = LEVELS[next(lv for lv in LEVELS if name.endswith(f"{lv})"))]
        text = " ".join(" ".join(r[:1]) for r in grid[:14])
        if "pence per kwh" not in text.lower():
            raise SourceError(SOURCE, f"table {table} {name}: the 'pence per kWh' unit line is missing")
        if band not in text:
            raise SourceError(SOURCE, f"table {table} {name}: the band definition {band!r} is missing (band changed?)")
        head = next((i for i, r in enumerate(grid) if r and r[0].strip() == "Year"), None)
        if head is None or COLUMN not in grid[head]:
            raise SourceError(SOURCE, f"table {table} {name}: header row with 'Year' and {COLUMN!r} not found")
        col, per, meth = grid[head].index(COLUMN), grid[head].index("Period"), grid[head].index("Methodology")
        n_rows = n_gaps = 0
        for r in grid[head + 1:]:
            m = _YEAR.match(r[0].strip()) if r else None
            if not m or len(r) <= col or r[meth].strip() != METHODOLOGY:
                continue
            n_rows += 1
            start, end = _period(int(m.group(1)), r[per], table)
            sid = f"desnz:qep_{table}:medium:{level}"
            if not r[col].strip():
                if gaps is None:
                    raise SourceError(SOURCE, f"table {table} {name}: blank value for {start}")
                n_gaps += 1
                gaps.append(gap(SOURCE, sid, "GB", start.isoformat(), end.isoformat(), "DESNZ published no value"))
                continue
            pence = _number(r[col], table, f"{name} {start}")
            out.append(validate_point({
                "source": SOURCE, "series_id": sid, "region": "GB", "layer": "cost", "buyer_type": buyer,
                "period_start": start.isoformat(), "period_end": end.isoformat(), "value": float(pence / 100),
                "unit": "GBP/kWh", "currency": "GBP", "as_of": retrieved_at[:10], "retrieved_at": retrieved_at,
                "raw_sha256": digest, "confidence": confidence,
            }))
        if n_rows < 20:
            raise SourceError(SOURCE, f"table {table} {name}: only {n_rows} rows on the {METHODOLOGY} methodology, expected 20 or more")
        check_gap_share(SOURCE, f"table {table} {name}", n_gaps, n_rows)
    return out
