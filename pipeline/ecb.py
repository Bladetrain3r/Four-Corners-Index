"""ECB euro foreign exchange reference rates (EXR), SDMX-CSV. Currency units per 1 EUR.

Licence: free use if the ECB is cited and any modification (such as a cross-rate via EUR) is stated.
RUB is included for history only: the ECB suspended it after 2022-03-01.
"""
from __future__ import annotations

import calendar
import csv
import io
import math
from datetime import date
from typing import Any

from pipeline.common import SourceError, sha256_hex, validate_point

SOURCE = "ecb"
COLUMNS = ("KEY", "FREQ", "CURRENCY", "CURRENCY_DENOM", "EXR_TYPE", "EXR_SUFFIX", "TIME_PERIOD", "OBS_VALUE")
CURRENCIES = {"USD", "CNY", "ZAR", "RUB", "GBP"}


def parse(raw: bytes, retrieved_at: str, confidence: str = "primary") -> list[dict[str, Any]]:
    what = "EXR"
    try:
        rd = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise SourceError(SOURCE, f"{what}: not UTF-8 text") from exc
    got = tuple(rd.fieldnames or ())
    missing = [c for c in COLUMNS if c not in got]
    if missing:
        raise SourceError(SOURCE, f"{what}: header changed, missing columns {missing}")
    digest = sha256_hex(raw)
    out = []
    for row in rd:
        cur = row["CURRENCY"]
        if cur not in CURRENCIES:
            raise SourceError(SOURCE, f"{what}: unexpected currency {cur!r}")
        if (row["CURRENCY_DENOM"], row["EXR_TYPE"], row["EXR_SUFFIX"]) != ("EUR", "SP00", "A"):
            raise SourceError(SOURCE, f"{what}: not a EUR spot average/reference series: {row['KEY']}")
        freq, t = row["FREQ"], row["TIME_PERIOD"]
        try:
            if freq == "D":
                start = end = date.fromisoformat(t)
            elif freq == "M":
                y, m = int(t[:4]), int(t[5:7])
                start, end = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
            else:
                raise SourceError(SOURCE, f"{what}: unsupported frequency {freq!r}")
            v = float(row["OBS_VALUE"])
        except ValueError as exc:
            raise SourceError(SOURCE, f"{what}: bad value or period in {row['KEY']} {t!r}: {row['OBS_VALUE']!r}") from exc
        if not math.isfinite(v) or v <= 0:
            raise SourceError(SOURCE, f"{what}: non-positive or non-finite rate {v} in {row['KEY']} {t}")
        out.append(validate_point({
            "source": SOURCE, "series_id": f"ecb:EXR:{freq}:{cur}:EUR", "region": cur, "layer": "driver",
            "period_start": start.isoformat(), "period_end": end.isoformat(), "value": v,
            "unit": f"{cur}/EUR", "currency": cur, "as_of": retrieved_at[:10], "retrieved_at": retrieved_at,
            "raw_sha256": digest, "confidence": confidence,
        }))
    if not out:
        raise SourceError(SOURCE, f"{what}: no observations")
    return out
