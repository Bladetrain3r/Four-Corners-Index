import json

import pytest

from pipeline import eia, ember, worldbank
from pipeline.common import SourceError


def test_eia_null_price_becomes_an_explicit_gap_when_asked(fixture_bytes):
    raw, m = fixture_bytes("eia", "henry_hub_spot_daily_2026-09.json")
    doc = json.loads(raw)
    doc["response"]["data"][3]["value"] = None
    day = doc["response"]["data"][3]["period"]
    gaps: list = []
    pts = eia.parse_henry_hub(json.dumps(doc).encode(), m["fetched_at"], "daily", gaps=gaps)
    assert len(pts) == 14 and len(gaps) == 1
    assert gaps[0]["period_start"] == day and gaps[0]["region"] == "US" and "no price" in gaps[0]["reason"]
    assert day not in {p["period_start"] for p in pts}  # nothing interpolated in its place
    with pytest.raises(SourceError, match=r"^\[eia\].*null"):  # strict by default
        eia.parse_henry_hub(json.dumps(doc).encode(), m["fetched_at"], "daily")


def test_mostly_empty_response_is_broken_not_a_few_gaps(fixture_bytes):
    raw, m = fixture_bytes("eia", "henry_hub_spot_daily_2026-09.json")
    doc = json.loads(raw)
    for r in doc["response"]["data"][:10]:
        r["value"] = None
    with pytest.raises(SourceError, match=r"^\[eia\].*10 of 15 rows are empty"):
        eia.parse_henry_hub(json.dumps(doc).encode(), m["fetched_at"], "daily", gaps=[])


def test_ember_blank_price_is_a_gap_with_reason_and_strict_otherwise(fixture_bytes):
    raw, m = fixture_bytes("ember", "price_monthly_sample.csv")
    lines = raw.decode().splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.startswith("Austria,AUT,2015-01-01"))
    lines[i] = "Austria,AUT,2015-01-01,"
    edited = "\n".join(lines).encode()
    gaps: list = []
    pts = ember.parse_prices(edited, m["fetched_at"], "monthly", gaps=gaps)
    assert [(g["region"], g["period_start"]) for g in gaps] == [("AT", "2015-01-01")]
    assert not [p for p in pts if p["region"] == "AT" and p["period_start"] == "2015-01-01"]
    with pytest.raises(SourceError, match=r"^\[ember\].*blank"):
        ember.parse_prices(edited, m["fetched_at"], "monthly")


def test_worldbank_not_available_marker_is_recorded_as_gap(fixture_bytes):
    raw, m = fixture_bytes("worldbank", "pink_sheet_monthly_gas_coal_last36.csv")
    edited = raw.replace(b"2026M08,135.2,96.8", b"2026M08,\xe2\x80\xa6,96.8")
    gaps: list = []
    worldbank.parse_csv_extract(edited, m["fetched_at"], gaps=gaps)
    assert [(g["series_id"], g["period_start"]) for g in gaps] == [("worldbank:pink_sheet:coal_australia", "2026-08-01")]
