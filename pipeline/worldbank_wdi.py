"""World Bank World Development Indicators: PM2.5 air pollution, mean annual exposure (EN.ATM.PM25.MC.M3). CC BY-4.0.

Population-weighted annual mean PM2.5 exposure in micrograms per cubic metre, a model estimate (the World Bank cites the
IHME Global Burden of Disease 2023 air pollution exposure estimates as its source). Annual, with a lag of about two and a
half years: the newest years come back as null and are recorded as gaps with that reason, never filled in.
"""
from __future__ import annotations

import json
import math
from datetime import date

from pipeline.common import SourceError, check_gap_share, gap, sha256_hex, validate_point

SOURCE = "worldbank"
INDICATOR = "EN.ATM.PM25.MC.M3"
SERIES_ID = f"worldbank:wdi:{INDICATOR}"
REGIONS = {"CHN": "CN", "EUU": "EU", "GBR": "GB", "RUS": "RU", "USA": "US", "ZAF": "ZA"}  # ISO3 as the API returns it -> our region ids
UNIT_WORDS = "micrograms per cubic meter"


def parse(raw: bytes, retrieved_at: str, gaps: list[dict] | None = None) -> list[dict]:
    try:
        doc = json.loads(raw)
        meta, rows = doc[0], doc[1]
    except (ValueError, IndexError, KeyError, TypeError) as exc:
        raise SourceError(SOURCE, f"wdi_pm25: not the expected [meta, rows] JSON ({type(exc).__name__}: {exc})") from exc
    if not isinstance(meta, dict) or not isinstance(rows, list):
        raise SourceError(SOURCE, "wdi_pm25: not the expected [meta, rows] JSON (message object instead of data?)")
    try:
        as_of = date.fromisoformat(meta["lastupdated"]).isoformat()
    except (KeyError, ValueError, TypeError) as exc:
        raise SourceError(SOURCE, f"wdi_pm25: no valid 'lastupdated' date in the response header: {meta!r}") from exc
    digest = sha256_hex(raw)
    out: list[dict] = []
    own_gaps: list[dict] = []
    for r in rows:
        ind = r.get("indicator", {})
        if ind.get("id") != INDICATOR or UNIT_WORDS not in ind.get("value", ""):
            raise SourceError(SOURCE, f"wdi_pm25: unexpected indicator {ind!r} (expected {INDICATOR} in {UNIT_WORDS})")
        iso3 = r.get("countryiso3code")
        if iso3 not in REGIONS:
            raise SourceError(SOURCE, f"wdi_pm25: unexpected area {iso3!r}; expected one of {sorted(REGIONS)}")
        try:
            year = int(r["date"])
        except (KeyError, ValueError, TypeError) as exc:
            raise SourceError(SOURCE, f"wdi_pm25: bad year {r.get('date')!r} for {iso3}") from exc
        start, end = date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()
        v = r.get("value")
        if v is None:
            own_gaps.append(gap(SOURCE, SERIES_ID, REGIONS[iso3], start, end, "the World Bank has not published a value for this year yet (about two and a half years of lag)"))
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise SourceError(SOURCE, f"wdi_pm25: value {v!r} for {iso3} {year} is not a positive finite number")
        out.append(validate_point({
            "source": SOURCE, "series_id": SERIES_ID, "region": REGIONS[iso3], "layer": "air", "period_start": start, "period_end": end,
            "value": float(v), "unit": "ug/m3", "as_of": as_of, "retrieved_at": retrieved_at, "raw_sha256": digest,
            "confidence": "high_latency"}))  # a model estimate published about two and a half years late
    check_gap_share(SOURCE, "wdi_pm25", len(own_gaps), len(rows))
    seen = {p["region"] for p in out}
    if seen != set(REGIONS.values()):
        raise SourceError(SOURCE, f"wdi_pm25: no values for {sorted(set(REGIONS.values()) - seen)}")
    if gaps is not None:
        gaps.extend(own_gaps)
    return out
