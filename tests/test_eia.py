import json

import pytest

from pipeline import eia
from pipeline.common import SourceError, dumps

RETAIL = "retail_sales_us_monthly_2025-01_onwards.json"
GEN = "operational_data_us_generation_monthly_2026-05_onwards.json"
HH_D = "henry_hub_spot_daily_2026-09.json"
HH_M = "henry_hub_spot_monthly_2025-10_onwards.json"


def _one(points, **want):
    hits = [p for p in points if all(p.get(k) == v for k, v in want.items())]
    assert len(hits) == 1, f"{len(hits)} matches for {want}"
    return hits[0]


def test_eia_retail_price_converted_exactly_to_usd_per_kwh(fixture_bytes, series_schema):
    raw, m = fixture_bytes("eia", RETAIL)
    pts = eia.parse_retail_price(raw, m["fetched_at"])
    for p in pts:
        series_schema.validate(p)
    res = _one(pts, buyer_type="household", period_start="2026-07-01")
    ind = _one(pts, buyer_type="industrial", period_start="2026-07-01")
    assert res["value"] == 0.1831 and ind["value"] == 0.0977  # 18.31 and 9.77 cents/kWh, no float drift
    assert res["unit"] == "USD/kWh" and res["currency"] == "USD" and res["region"] == "US"
    assert res["period_end"] == "2026-07-31" and res["as_of"] == m["fetched_at"][:10]


def test_eia_retail_skips_commercial_and_all_sector_explicitly(fixture_bytes):
    raw, m = fixture_bytes("eia", RETAIL)
    pts = eia.parse_retail_price(raw, m["fetched_at"])
    assert {p["buyer_type"] for p in pts} == {"household", "industrial"}
    assert len(pts) == 2 * 19  # 19 months (2025-01..2026-07) of RES and IND


def test_eia_generation_units_fuels_and_no_aggregate_double_count(fixture_bytes, series_schema):
    raw, m = fixture_bytes("eia", GEN)
    pts = eia.parse_generation(raw, m["fetched_at"])
    for p in pts:
        series_schema.validate(p)
    fuels = {p["fuel"] for p in pts}
    assert {"total", "gas", "coal", "nuclear", "solar", "wind", "hydro"} <= fuels
    assert "AOR" not in json.dumps(pts)
    ng = _one(pts, fuel="gas", period_start="2026-07-01")
    tot = _one(pts, fuel="total", period_start="2026-07-01")
    assert abs(ng["value"] - 205294) < 1 and abs(tot["value"] - 453744.39758) < 1e-6 and ng["unit"] == "GWh"
    assert _one(pts, fuel="pumped_storage", period_start="2026-07-01")["value"] < 0  # net storage can be negative


def test_eia_henry_hub_daily_and_monthly(fixture_bytes, series_schema):
    raw, m = fixture_bytes("eia", HH_D)
    d = eia.parse_henry_hub(raw, m["fetched_at"], "daily")
    for p in d:
        series_schema.validate(p)
    last = _one(d, period_start="2026-09-22")
    assert last["value"] == 2.9 and last["unit"] == "USD/MMBtu" and last["period_end"] == "2026-09-22"
    raw, m = fixture_bytes("eia", HH_M)
    mo = eia.parse_henry_hub(raw, m["fetched_at"], "monthly")
    assert _one(mo, period_start="2026-08-01")["value"] == 2.78


def test_eia_output_deterministic(fixture_bytes):
    raw, m = fixture_bytes("eia", RETAIL)
    assert dumps(eia.parse_retail_price(raw, m["fetched_at"])) == dumps(eia.parse_retail_price(raw, m["fetched_at"]))


def test_eia_corrupted_units_fail_naming_source(fixture_bytes):
    raw, m = fixture_bytes("eia", RETAIL)
    with pytest.raises(SourceError, match=r"^\[eia\].*expected cents per kilowatt-hour"):
        eia.parse_retail_price(raw.replace(b"cents per kilowatt-hour", b"dollars per kilowatt-hour"), m["fetched_at"])


def test_eia_renamed_column_fails_not_silently_skips(fixture_bytes):
    raw, m = fixture_bytes("eia", RETAIL)
    with pytest.raises(SourceError, match=r"^\[eia\].*price"):
        eia.parse_retail_price(raw.replace(b'"price"', b'"prix"'), m["fetched_at"])


def test_eia_null_and_text_values_fail(fixture_bytes):
    raw, m = fixture_bytes("eia", RETAIL)
    doc = json.loads(raw)
    row = next(r for r in doc["response"]["data"] if r["sectorid"] == "RES")  # data[0] is ALL, which is skipped
    row["price"] = None
    with pytest.raises(SourceError, match=r"^\[eia\].*null"):
        eia.parse_retail_price(json.dumps(doc).encode(), m["fetched_at"])
    row["price"] = "NaN"
    with pytest.raises(SourceError, match=r"^\[eia\].*not finite"):
        eia.parse_retail_price(json.dumps(doc).encode(), m["fetched_at"])


def test_eia_unknown_fuel_and_error_body_fail(fixture_bytes):
    raw, m = fixture_bytes("eia", GEN)
    with pytest.raises(SourceError, match=r"^\[eia\].*unknown fueltypeid"):
        eia.parse_generation(raw.replace(b'"NUC"', b'"XYZ"', 1), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[eia\].*not an EIA v2"):
        eia.parse_generation(b'{"error":"API_KEY_INVALID"}', m["fetched_at"])


def test_eia_wrong_frequency_fails(fixture_bytes):
    raw, m = fixture_bytes("eia", HH_D)
    with pytest.raises(SourceError, match=r"^\[eia\].*frequency"):
        eia.parse_henry_hub(raw, m["fetched_at"], "monthly")
