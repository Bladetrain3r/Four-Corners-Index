"""World Bank Commodity Price Data (the Pink Sheet), monthly, nominal US dollars. CC BY 4.0.

The live source is an XLSX ("Monthly Prices" sheet). `read_xlsx_sheet` (stdlib zipfile + XML) and `read_csv_grid`
both produce a grid of cell strings, which `parse_grid` turns into series. The committed fixture is a CSV extract
of the real workbook; the real workbook is parsed live in evidence/G2.md.
"""
from __future__ import annotations

import calendar
import math
import re
from datetime import date

from pipeline import xlsx
from pipeline.common import SourceError, gap, sha256_hex, validate_point
from pipeline.xlsx import read_csv_grid

SOURCE = "worldbank"
SHEET = "Monthly Prices"

# column name (as published, footnote marks stripped) -> (series slug, region, fuel, unit, expected sheet unit)
COLUMNS = {
    "Coal, Australian": ("coal_australia", "AU", "coal", "USD/t", "($/mt)"),
    "Coal, South African": ("coal_south_africa", "ZA", "coal", "USD/t", "($/mt)"),
    "Natural gas, US": ("natural_gas_us", "US", "gas", "USD/MMBtu", "($/mmbtu)"),
    "Natural gas, Europe": ("natural_gas_europe", "EU", "gas", "USD/MMBtu", "($/mmbtu)"),
    "Liquefied natural gas, Japan": ("lng_japan", "JP", "gas", "USD/MMBtu", "($/mmbtu)"),
}
ESTIMATE_LAST_N = {"lng_japan": 2}  # Description sheet: "recent two months' averages are estimates"
_MONTH = re.compile(r"^(\d{4})M(\d{2})$")
_UPDATED = re.compile(r"Updated on ([A-Za-z]+ \d{1,2}, \d{4})")


def read_xlsx_sheet(raw: bytes, sheet: str = SHEET) -> list[list[str]]:
    return xlsx.read_xlsx_sheet(raw, sheet, SOURCE)


def _parse_updated(text: str) -> str:
    """'September 02, 2026' -> '2026-09-02'."""
    month_name, day, year = re.match(r"([A-Za-z]+) (\d{1,2}), (\d{4})", text).groups()  # type: ignore[union-attr]
    months = {n: i for i, n in enumerate(calendar.month_name) if n}
    if month_name not in months:
        raise SourceError(SOURCE, f"bad month name in 'Updated on' line: {text!r}")
    return date(int(year), months[month_name], int(day)).isoformat()


def parse_grid(grid: list[list[str]], raw: bytes, retrieved_at: str, confidence: str = "primary",
               gaps: list[dict] | None = None) -> list[dict]:
    as_of = None
    for row in grid[:8]:
        for cell in row:
            m = _UPDATED.search(cell or "")
            if m:
                as_of = _parse_updated(m.group(1))
    if as_of is None:
        raise SourceError(SOURCE, "no 'Updated on <date>' line in the first rows")
    known = tuple(COLUMNS)
    header_i = next((i for i, r in enumerate(grid[:15]) if any(k in (c or "") for c in r for k in known)), None)
    if header_i is None:
        raise SourceError(SOURCE, f"column header row (with any of {list(known)}) not found in the first rows")
    names = [re.sub(r"\s*\*+$", "", (c or "").strip()) for c in grid[header_i]]
    units = [(c or "").strip().lower() for c in grid[header_i + 1]]
    cols = {}
    for name, (slug, region, fuel, unit, sheet_unit) in COLUMNS.items():
        if name not in names:
            raise SourceError(SOURCE, f"expected column {name!r} is missing (columns: {names})")
        i = names.index(name)
        if i >= len(units) or units[i] != sheet_unit:
            raise SourceError(SOURCE, f"column {name!r} has unit {units[i] if i < len(units) else None!r}, expected {sheet_unit!r}")
        cols[i] = (slug, region, fuel, unit)
    digest = sha256_hex(raw)
    per_slug: dict[str, list[dict]] = {}
    for row in grid[header_i + 2:]:
        if not row or not row[0]:
            continue
        m = _MONTH.match(row[0].strip())
        if not m:
            raise SourceError(SOURCE, f"unrecognised period label {row[0]!r}")
        y, mo = int(m.group(1)), int(m.group(2))
        start, end = date(y, mo, 1), date(y, mo, calendar.monthrange(y, mo)[1])
        for i, (slug, region, fuel, unit) in cols.items():
            cell = (row[i] if i < len(row) else "").strip()
            if cell in ("", "…", "..."):  # published as not available: a gap, never interpolated
                if gaps is not None and cell:
                    gaps.append(gap(SOURCE, f"worldbank:pink_sheet:{slug}", region, start.isoformat(), end.isoformat(),
                                    "World Bank marks this month not available"))
                continue
            try:
                v = float(cell)
            except ValueError as exc:
                raise SourceError(SOURCE, f"value {cell!r} in column {slug} at {row[0]} is not numeric") from exc
            if not math.isfinite(v):
                raise SourceError(SOURCE, f"non-finite value in column {slug} at {row[0]}")
            per_slug.setdefault(slug, []).append(validate_point({
                "source": SOURCE, "series_id": f"worldbank:pink_sheet:{slug}", "region": region, "layer": "driver",
                "fuel": fuel, "period_start": start.isoformat(), "period_end": end.isoformat(), "value": v,
                "unit": unit, "currency": "USD", "as_of": as_of, "retrieved_at": retrieved_at,
                "raw_sha256": digest, "confidence": confidence,
            }))
    out = []
    for slug, pts in per_slug.items():
        n_est = ESTIMATE_LAST_N.get(slug, 0)
        if n_est:
            for p in pts[-n_est:]:
                p["source_flag"] = "estimate"
        out.extend(pts)
    if not out:
        raise SourceError(SOURCE, "no observations")
    return out


def parse_csv_extract(raw: bytes, retrieved_at: str, gaps: list[dict] | None = None) -> list[dict]:
    return parse_grid(read_csv_grid(raw), raw, retrieved_at, gaps=gaps)


def parse_xlsx(raw: bytes, retrieved_at: str, gaps: list[dict] | None = None) -> list[dict]:
    return parse_grid(read_xlsx_sheet(raw), raw, retrieved_at, gaps=gaps)
