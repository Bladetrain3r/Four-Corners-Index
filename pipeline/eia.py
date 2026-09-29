"""EIA adapter (API v2, keyed): retail-sales price, electric-power-operational-data generation, Henry Hub spot.

EIA responses carry no publication date, so `as_of` is the fetch date. Values arrive as JSON strings.
The API key is never handled here: URLs recorded elsewhere carry api_key=REDACTED.
"""
from __future__ import annotations

import calendar
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from pipeline.common import SourceError, sha256_hex, validate_point

SOURCE = "eia"

SECTOR_BUYER = {"RES": "household", "IND": "industrial"}
SECTOR_SKIP = {"COM", "ALL", "TRA", "OTH"}  # not a SPEC buyer type; explicit so a new code is loud
FUEL = {
    "ALL": "total", "NG": "gas", "COL": "coal", "NUC": "nuclear", "WND": "wind", "SUN": "solar",
    "HYC": "hydro", "PET": "oil", "BIO": "bioenergy", "GEO": "other", "OTH": "other",
    "HPS": "pumped_storage",
}
FUEL_SKIP = {"AOR", "REN", "FOS"}  # EIA aggregates, double count the fuels above


def _rows(raw: bytes, what: str, expect_freq: str) -> list[dict[str, Any]]:
    try:
        doc = json.loads(raw)
        resp = doc["response"]
        rows = resp["data"]
        freq = resp["frequency"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError(SOURCE, f"{what}: not an EIA v2 data response ({exc!r})") from exc
    if freq != expect_freq:
        raise SourceError(SOURCE, f"{what}: frequency {freq!r}, expected {expect_freq!r}")
    if not rows:
        raise SourceError(SOURCE, f"{what}: response holds no rows")
    return rows


def _number(row: dict[str, Any], col: str, what: str) -> Decimal:
    v = row.get(col)
    if v in (None, ""):
        raise SourceError(SOURCE, f"{what}: `{col}` is null or missing at {row.get('period')}")
    try:
        d = Decimal(str(v))
    except InvalidOperation as exc:
        raise SourceError(SOURCE, f"{what}: `{col}` not numeric ({v!r}) at {row.get('period')}") from exc
    if not d.is_finite():
        raise SourceError(SOURCE, f"{what}: `{col}` not finite at {row.get('period')}")
    return d


def _bounds(period: str, what: str) -> tuple[date, date]:
    try:
        if len(period) == 7:
            y, m = int(period[:4]), int(period[5:])
            return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
        d = date.fromisoformat(period)
        return d, d
    except ValueError as exc:
        raise SourceError(SOURCE, f"{what}: bad period {period!r}") from exc


def _base(raw: bytes, retrieved_at: str, confidence: str) -> dict[str, Any]:
    return {"source": SOURCE, "as_of": retrieved_at[:10], "retrieved_at": retrieved_at,
            "raw_sha256": sha256_hex(raw), "confidence": confidence}


def parse_retail_price(raw: bytes, retrieved_at: str, confidence: str = "primary") -> list[dict[str, Any]]:
    what = "retail-sales"
    out = []
    for r in _rows(raw, what, "monthly"):
        sector = r.get("sectorid")
        if sector in SECTOR_SKIP:
            continue
        if sector not in SECTOR_BUYER:
            raise SourceError(SOURCE, f"{what}: unknown sectorid {sector!r}")
        if r.get("price-units") != "cents per kilowatt-hour":
            raise SourceError(SOURCE, f"{what}: price units {r.get('price-units')!r}, expected cents per kilowatt-hour")
        start, end = _bounds(r["period"], what)
        p = _base(raw, retrieved_at, confidence) | {
            "series_id": f"electricity/retail-sales:price:{sector}", "region": r["stateid"], "layer": "cost",
            "buyer_type": SECTOR_BUYER[sector], "period_start": start.isoformat(), "period_end": end.isoformat(),
            "value": float(_number(r, "price", what) / 100), "unit": "USD/kWh", "currency": "USD",
        }
        out.append(validate_point(p))
    return out


def parse_generation(raw: bytes, retrieved_at: str, confidence: str = "primary") -> list[dict[str, Any]]:
    what = "electric-power-operational-data"
    out = []
    for r in _rows(raw, what, "monthly"):
        code = r.get("fueltypeid")
        if code in FUEL_SKIP:
            continue
        if code not in FUEL:
            raise SourceError(SOURCE, f"{what}: unknown fueltypeid {code!r}")
        if r.get("generation-units") != "thousand megawatthours":
            raise SourceError(SOURCE, f"{what}: units {r.get('generation-units')!r}, expected thousand megawatthours")
        start, end = _bounds(r["period"], what)
        p = _base(raw, retrieved_at, confidence) | {
            "series_id": "electricity/electric-power-operational-data:generation", "region": r["location"],
            "layer": "mix", "fuel": FUEL[code], "period_start": start.isoformat(), "period_end": end.isoformat(),
            "value": float(_number(r, "generation", what)), "unit": "GWh",  # thousand MWh == GWh
        }
        out.append(validate_point(p))
    return out


def parse_henry_hub(raw: bytes, retrieved_at: str, frequency: str, confidence: str = "primary") -> list[dict[str, Any]]:
    what = f"henry-hub-{frequency}"
    out = []
    for r in _rows(raw, what, frequency):
        if r.get("series") != "RNGWHHD":
            raise SourceError(SOURCE, f"{what}: series {r.get('series')!r}, expected RNGWHHD")
        if r.get("units") != "$/MMBTU":
            raise SourceError(SOURCE, f"{what}: units {r.get('units')!r}, expected $/MMBTU")
        start, end = _bounds(r["period"], what)
        p = _base(raw, retrieved_at, confidence) | {
            "series_id": f"natural-gas/pri/fut:RNGWHHD:{frequency}", "region": "US", "layer": "driver",
            "fuel": "gas", "period_start": start.isoformat(), "period_end": end.isoformat(),
            "value": float(_number(r, "value", what)), "unit": "USD/MMBtu", "currency": "USD",
        }
        out.append(validate_point(p))
    return out
