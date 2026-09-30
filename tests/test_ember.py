import pytest

from pipeline import ember
from pipeline.common import SourceError, dumps

MONTHLY = "monthly_generation_global_sample.csv"
YEARLY = "yearly_generation_global_sample.csv"
PRICE_M = "price_monthly_sample.csv"
PRICE_D = "price_daily_sample.csv"


def _one(points, **want):
    hits = [p for p in points if all(p.get(k) == v for k, v in want.items())]
    assert len(hits) == 1, f"{len(hits)} matches for {want}"
    return hits[0]


def test_ember_monthly_generation_totals_intensity_and_units(fixture_bytes, series_schema):
    raw, m = fixture_bytes("ember", MONTHLY)
    pts = ember.parse_generation(raw, m["fetched_at"], "monthly", as_of="2026-09-18")
    for p in pts:
        series_schema.validate(p)
    eu = _one(pts, region="EU", fuel="total", series_id="ember:monthly:generation", period_start="2026-08-01")
    assert eu["value"] == 214.481 and eu["unit"] == "TWh" and eu["period_end"] == "2026-08-31"
    assert eu["as_of"] == "2026-09-18"
    ci = _one(pts, region="EU", series_id="ember:monthly:emissions_intensity", period_start="2026-08-01")
    assert ci["value"] == 215.991 and ci["unit"] == "gCO2e/kWh"
    us = _one(pts, region="US", fuel="total", series_id="ember:monthly:generation", period_start="2026-08-01")
    assert us["value"] == 465.153


def test_ember_russia_is_low_confidence_and_others_primary(fixture_bytes):
    raw, m = fixture_bytes("ember", MONTHLY)
    pts = ember.parse_generation(raw, m["fetched_at"], "monthly")
    ru = _one(pts, region="RU", fuel="total", series_id="ember:monthly:generation", period_start="2026-07-01")
    assert ru["value"] == 84.947 and ru["confidence"] == "low_confidence"
    assert {p["confidence"] for p in pts if p["region"] != "RU"} == {"primary"}


def test_ember_aggregates_skipped_and_fuels_mapped(fixture_bytes):
    raw, m = fixture_bytes("ember", MONTHLY)
    pts = ember.parse_generation(raw, m["fetched_at"], "monthly")
    fuels = {p["fuel"] for p in pts}
    assert {"coal", "gas", "nuclear", "hydro", "wind", "solar", "total", "demand"} <= fuels
    assert not fuels & {"clean", "fossil", "renewables"}


def test_ember_yearly_demand_for_weights(fixture_bytes):
    raw, m = fixture_bytes("ember", YEARLY)
    pts = ember.parse_generation(raw, m["fetched_at"], "yearly")
    want = {"CN": 10486.272, "EU": 2774.435, "RU": 1177.295, "ZA": 236.84, "US": 4532.142}
    for region, twh in want.items():
        d = _one(pts, region=region, fuel="demand", series_id="ember:yearly:generation", period_start="2025-01-01")
        assert d["value"] == twh and d["period_end"] == "2025-12-31"


def test_ember_prices_monthly_and_daily_with_eurostat_country_codes(fixture_bytes, series_schema):
    raw, m = fixture_bytes("ember", PRICE_M)
    pts = ember.parse_prices(raw, m["fetched_at"], "monthly")
    for p in pts:
        series_schema.validate(p)
    at = _one(pts, region="AT", period_start="2015-01-01")
    assert at["value"] == 29.94 and at["unit"] == "EUR/MWh" and at["buyer_type"] == "wholesale"
    assert {"EL", "GB", "DE"} <= {p["region"] for p in pts}  # Greece is EL (Eurostat), not GR
    raw, m = fixture_bytes("ember", PRICE_D)
    d = ember.parse_prices(raw, m["fetched_at"], "daily")
    assert _one(d, region="AT", period_start="2015-01-01")["value"] == 22.34


def test_ember_output_deterministic(fixture_bytes):
    raw, m = fixture_bytes("ember", PRICE_M)
    assert dumps(ember.parse_prices(raw, m["fetched_at"])) == dumps(ember.parse_prices(raw, m["fetched_at"]))


def test_ember_renamed_header_fails_naming_source(fixture_bytes):
    raw, m = fixture_bytes("ember", MONTHLY)
    with pytest.raises(SourceError, match=r"^\[ember\].*header changed.*Generation \(TWh\)"):
        ember.parse_generation(raw.replace(b"Generation (TWh)", b"Generation (GWh)", 1), m["fetched_at"], "monthly")
    raw, m = fixture_bytes("ember", PRICE_M)
    with pytest.raises(SourceError, match=r"^\[ember\].*header changed"):
        ember.parse_prices(raw.replace(b"ISO3 Code", b"ISO 3 code", 1), m["fetched_at"])


def test_ember_old_long_format_fails_loudly(fixture_bytes):
    old = b"Area,Year,Category,Variable,Unit,Value\nChina,2020,Electricity generation,Coal,TWh,4000\n"
    with pytest.raises(SourceError, match=r"^\[ember\].*header changed"):
        ember.parse_generation(old, "2026-09-29T00:00:00Z", "yearly")


def test_ember_unknown_source_blank_and_text_values_fail(fixture_bytes):
    raw, m = fixture_bytes("ember", MONTHLY)
    with pytest.raises(SourceError, match=r"^\[ember\].*unknown electricity source"):
        ember.parse_generation(raw.replace(b",Coal,", b",Peat,", 1), m["fetched_at"], "monthly")
    lines = raw.decode().splitlines()
    i = next(n for n, ln in enumerate(lines) if ",Gas," in ln and ln.startswith("EU,"))
    cols = lines[i].split(",")
    cols[6] = ""
    lines[i] = ",".join(cols)
    with pytest.raises(SourceError, match=r"^\[ember\].*blank"):
        ember.parse_generation("\n".join(lines).encode(), m["fetched_at"], "monthly")
    cols[6] = "n/a"
    lines[i] = ",".join(cols)
    with pytest.raises(SourceError, match=r"^\[ember\].*not numeric"):
        ember.parse_generation("\n".join(lines).encode(), m["fetched_at"], "monthly")


def test_ember_unknown_country_and_mid_month_date_fail(fixture_bytes):
    raw, m = fixture_bytes("ember", PRICE_M)
    with pytest.raises(SourceError, match=r"^\[ember\].*unknown country code"):
        ember.parse_prices(raw.replace(b",AUT,", b",XXX,", 1), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[ember\].*first of the month"):
        ember.parse_prices(raw.replace(b"2015-01-01", b"2015-01-15", 1), m["fetched_at"])
