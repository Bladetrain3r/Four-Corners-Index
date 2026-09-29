"""Ember adapter (CC-BY-4.0, keyless CSV): monthly and yearly generation/demand/carbon intensity, EU day-ahead prices.

Ember changed its download format in July 2026 (one row per area, period and source). Every parser checks the
exact header and fails loudly, naming the source, if a column is missing or renamed. Ember's page dates are
unreliable, so `as_of` comes from the caller (the file's Last-Modified date), falling back to the fetch date.
"""
from __future__ import annotations

import calendar
import csv
import io
import math
from datetime import date
from typing import Any

from pipeline.common import SourceError, sha256_hex, validate_point

SOURCE = "ember"

GEN_COLUMNS_MONTHLY = (
    "Area", "ISO 3 code", "Date", "Area type", "Electricity source", "Is aggregated source", "Generation (TWh)",
    "Generation YoY change (TWh)", "Generation YoY change (%)", "Share of generation (%)",
    "Share of generation YoY change (% points)", "Emissions (MtCO2e)", "Emissions YoY change (MtCO2e)",
    "Emissions YoY change (%)", "Share of emissions (%)", "Emissions intensity (gCO2e/kWh)", "Continent",
    "Ember region", "EU member", "OECD member", "G20 member", "G7 member", "ASEAN member",
)
GEN_COLUMNS_YEARLY = tuple(("Year" if c == "Date" else c) for c in GEN_COLUMNS_MONTHLY[:11]) + (
    "Capacity (GW)",) + GEN_COLUMNS_MONTHLY[11:]
PRICE_COLUMNS = ("Country", "ISO3 Code", "Date", "Price (EUR/MWhe)")

AREA_REGION = {"EU": "EU", "China": "CN", "Russia": "RU", "South Africa": "ZA", "United States": "US"}
AREA_CONFIDENCE = {"Russia": "low_confidence"}  # Ziggy, STOP-1 decision 9
# Ember source name -> fuel field. Aggregates are skipped explicitly (derivable from the fuels).
FUEL = {
    "Coal": "coal", "Gas": "gas", "Other fossil": "other_fossil", "Nuclear": "nuclear", "Hydro": "hydro",
    "Wind": "wind", "Solar": "solar", "Bioenergy": "bioenergy", "Other renewables": "other_renewables",
    "Total generation": "total", "Demand": "demand", "Net imports": "net_imports",
}
AGGREGATES = {"Clean", "Fossil", "Renewables", "Wind and solar", "Hydro, bioenergy and other renewables"}
# ISO3 -> the two-letter codes Eurostat uses (Greece is EL there, the United Kingdom GB).
ISO3 = {
    "ALB": "AL", "AUT": "AT", "BEL": "BE", "BGR": "BG", "HRV": "HR", "CZE": "CZ", "DNK": "DK", "EST": "EE",
    "FIN": "FI", "FRA": "FR", "DEU": "DE", "GRC": "EL", "HUN": "HU", "IRL": "IE", "ITA": "IT", "LVA": "LV",
    "LTU": "LT", "LUX": "LU", "MNE": "ME", "NLD": "NL", "MKD": "MK", "NOR": "NO", "POL": "PL", "PRT": "PT",
    "ROU": "RO", "SRB": "RS", "SVK": "SK", "SVN": "SI", "ESP": "ES", "SWE": "SE", "CHE": "CH", "GBR": "GB",
}


def _reader(raw: bytes, expected: tuple[str, ...], what: str) -> csv.DictReader:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceError(SOURCE, f"{what}: not UTF-8 text") from exc
    rd = csv.DictReader(io.StringIO(text))
    got = tuple(rd.fieldnames or ())
    missing = [c for c in expected if c not in got]
    if missing:
        raise SourceError(SOURCE, f"{what}: header changed, missing columns {missing}")
    return rd


def _num(row: dict[str, str], col: str, what: str) -> float:
    v = (row.get(col) or "").strip()
    if v == "":
        raise SourceError(SOURCE, f"{what}: blank `{col}` for {row.get('Area') or row.get('Country')} {row.get('Date') or row.get('Year')}")
    try:
        x = float(v)
    except ValueError as exc:
        raise SourceError(SOURCE, f"{what}: `{col}` not numeric ({v!r})") from exc
    if not math.isfinite(x):
        raise SourceError(SOURCE, f"{what}: `{col}` not finite")
    return x


def _month(text: str, what: str) -> tuple[date, date]:
    try:
        d = date.fromisoformat(text)
    except ValueError as exc:
        raise SourceError(SOURCE, f"{what}: bad date {text!r}") from exc
    if d.day != 1:
        raise SourceError(SOURCE, f"{what}: monthly date {text!r} is not the first of the month")
    return d, date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _common(raw: bytes, retrieved_at: str, as_of: str | None) -> dict[str, Any]:
    return {"source": SOURCE, "as_of": as_of or retrieved_at[:10], "retrieved_at": retrieved_at,
            "raw_sha256": sha256_hex(raw)}


def parse_generation(raw: bytes, retrieved_at: str, period: str = "monthly", as_of: str | None = None,
                     areas: tuple[str, ...] = tuple(AREA_REGION)) -> list[dict[str, Any]]:
    """Generation by fuel, demand and carbon intensity for the wanted areas. period: 'monthly' or 'yearly'."""
    what = f"{period} generation"
    yearly = period == "yearly"
    date_col = "Year" if yearly else "Date"
    rd = _reader(raw, GEN_COLUMNS_YEARLY if yearly else GEN_COLUMNS_MONTHLY, what)
    base = _common(raw, retrieved_at, as_of)
    out = []
    for row in rd:
        area = row["Area"]
        if area not in areas:
            continue
        if area not in AREA_REGION:
            raise SourceError(SOURCE, f"{what}: no region code for area {area!r}")
        source_name = row["Electricity source"]
        if source_name in AGGREGATES:
            continue
        if source_name not in FUEL:
            raise SourceError(SOURCE, f"{what}: unknown electricity source {source_name!r} for {area}")
        if yearly:
            try:
                y = int(row[date_col])
            except ValueError as exc:
                raise SourceError(SOURCE, f"{what}: bad year {row[date_col]!r}") from exc
            start, end = date(y, 1, 1), date(y, 12, 31)
        else:
            start, end = _month(row[date_col], what)
        common = base | {
            "region": AREA_REGION[area], "layer": "mix", "fuel": FUEL[source_name],
            "period_start": start.isoformat(), "period_end": end.isoformat(),
            "confidence": AREA_CONFIDENCE.get(area, "primary"),
        }
        out.append(validate_point(common | {
            "series_id": f"ember:{period}:generation", "value": _num(row, "Generation (TWh)", what), "unit": "TWh",
        }))
        if source_name == "Total generation":
            out.append(validate_point(common | {
                "series_id": f"ember:{period}:emissions_intensity",
                "value": _num(row, "Emissions intensity (gCO2e/kWh)", what), "unit": "gCO2e/kWh",
            }))
    if not out:
        raise SourceError(SOURCE, f"{what}: no rows for areas {list(areas)}")
    return out


def parse_prices(raw: bytes, retrieved_at: str, period: str = "monthly", as_of: str | None = None) -> list[dict[str, Any]]:
    """European wholesale (day-ahead) price per country, EUR/MWh, load-weighted average per Ember. period: monthly|daily."""
    what = f"{period} wholesale price"
    rd = _reader(raw, PRICE_COLUMNS, what)
    base = _common(raw, retrieved_at, as_of)
    out = []
    for row in rd:
        iso = row["ISO3 Code"]
        if iso not in ISO3:
            raise SourceError(SOURCE, f"{what}: unknown country code {iso!r} ({row['Country']})")
        if period == "monthly":
            start, end = _month(row["Date"], what)
        else:
            try:
                start = end = date.fromisoformat(row["Date"])
            except ValueError as exc:
                raise SourceError(SOURCE, f"{what}: bad date {row['Date']!r}") from exc
        out.append(validate_point(base | {
            "series_id": f"ember:{period}:day_ahead_price", "region": ISO3[iso], "layer": "cost",
            "buyer_type": "wholesale", "period_start": start.isoformat(), "period_end": end.isoformat(),
            "value": _num(row, "Price (EUR/MWhe)", what), "unit": "EUR/MWh", "currency": "EUR",
            "confidence": "primary",
        }))
    if not out:
        raise SourceError(SOURCE, f"{what}: no rows")
    return out
