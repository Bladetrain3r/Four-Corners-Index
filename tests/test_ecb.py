import pytest

from pipeline import ecb
from pipeline.common import SourceError, dumps

DAILY = "exr_daily_usd_cny_zar_2026-06-01.csv"
MONTHLY = "exr_monthly_usd_cny_zar_2022-01.csv"
FULL = "exr_daily_usd_cny_zar_rub_last1_full.csv"


def _one(points, **want):
    hits = [p for p in points if all(p.get(k) == v for k, v in want.items())]
    assert len(hits) == 1, f"{len(hits)} matches for {want}"
    return hits[0]


def test_ecb_daily_rates_units_and_latest_values(fixture_bytes, series_schema):
    raw, m = fixture_bytes("ecb", FULL)
    pts = ecb.parse(raw, m["fetched_at"])
    for p in pts:
        series_schema.validate(p)
    assert _one(pts, region="CNY")["value"] == 7.6117 and _one(pts, region="CNY")["unit"] == "CNY/EUR"
    assert _one(pts, region="USD", period_start="2026-09-29")["value"] == 1.1355
    assert _one(pts, region="ZAR", period_start="2026-09-29")["value"] == 18.5887
    assert _one(pts, region="RUB")["period_start"] == "2022-03-01"  # last ECB rouble rate, history only


def test_ecb_daily_series_since_june(fixture_bytes):
    raw, m = fixture_bytes("ecb", DAILY)
    pts = ecb.parse(raw, m["fetched_at"])
    assert {p["region"] for p in pts} == {"USD", "CNY", "ZAR"}
    assert _one(pts, region="CNY", period_start="2026-06-01")["value"] == 7.8786
    assert all(p["period_start"] == p["period_end"] for p in pts)


def test_ecb_monthly_period_is_the_whole_month(fixture_bytes):
    raw, m = fixture_bytes("ecb", MONTHLY)
    pts = ecb.parse(raw, m["fetched_at"])
    aug = [p for p in pts if p["region"] == "USD" and p["period_start"] == "2026-08-01"]
    assert len(aug) == 1 and aug[0]["period_end"] == "2026-08-31" and abs(aug[0]["value"] - 1.1593095238095241) < 1e-9


def test_ecb_deterministic(fixture_bytes):
    raw, m = fixture_bytes("ecb", MONTHLY)
    assert dumps(ecb.parse(raw, m["fetched_at"])) == dumps(ecb.parse(raw, m["fetched_at"]))


def test_ecb_renamed_column_fails_naming_source(fixture_bytes):
    raw, m = fixture_bytes("ecb", DAILY)
    with pytest.raises(SourceError, match=r"^\[ecb\].*header changed.*OBS_VALUE"):
        ecb.parse(raw.replace(b"OBS_VALUE", b"OBSVALUE", 1), m["fetched_at"])


def test_ecb_wrong_series_type_and_currency_fail(fixture_bytes):
    raw, m = fixture_bytes("ecb", DAILY)
    with pytest.raises(SourceError, match=r"^\[ecb\].*not a EUR spot"):
        ecb.parse(raw.replace(b",SP00,A,", b",FM00,A,", 1), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[ecb\].*unexpected currency"):
        ecb.parse(raw.replace(b",CNY,EUR,", b",JPY,EUR,", 1), m["fetched_at"])


def test_ecb_blank_zero_and_text_rates_fail(fixture_bytes):
    raw, m = fixture_bytes("ecb", DAILY)
    for bad in (b",", b"0", b"n/a"):
        lines = raw.decode().splitlines()
        cols = lines[1].split(",")
        cols[7] = bad.decode() if bad != b"," else ""
        lines[1] = ",".join(cols)
        with pytest.raises(SourceError, match=r"^\[ecb\]"):
            ecb.parse("\n".join(lines).encode(), m["fetched_at"])
