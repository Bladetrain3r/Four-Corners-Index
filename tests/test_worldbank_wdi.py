"""World Bank WDI PM2.5 exposure adapter, against a real (trimmed) response."""

import json

import pytest

from pipeline import fetch, registry, worldbank_wdi
from pipeline.common import SourceError

FIXTURE = "wdi_pm25_exposure_2010_onwards.json"


@pytest.fixture
def points(fixture_bytes):
    raw, entry = fixture_bytes("worldbank", FIXTURE)
    gaps: list = []
    return worldbank_wdi.parse(raw, entry["fetched_at"], gaps), gaps, raw


def test_wdi_all_six_regions_parse_and_validate_against_the_schema(points, series_schema):
    pts, _, _ = points
    assert {p["region"] for p in pts} == {"CN", "EU", "GB", "RU", "US", "ZA"}
    for p in pts:
        assert not list(series_schema.iter_errors(p)), p
    assert all(p["layer"] == "air" and p["unit"] == "ug/m3" and p["confidence"] == "high_latency" for p in pts)


def test_wdi_values_are_the_published_ones_and_the_latest_year_is_2023(points):
    pts, _, raw = points
    rows = {(r["countryiso3code"], r["date"]): r["value"] for r in json.loads(raw)[1] if r["value"] is not None}
    assert len(pts) == len(rows)
    for p in pts:
        iso3 = {v: k for k, v in worldbank_wdi.REGIONS.items()}[p["region"]]
        assert p["value"] == rows[(iso3, p["period_start"][:4])]
    assert {p["period_start"][:4] for p in pts if p["region"] == "CN"} >= {"2010", "2023"} and max(p["period_end"] for p in pts) == "2023-12-31"
    assert all(0 < p["value"] < 200 for p in pts)  # µg/m³ of annual mean exposure: a sanity range, not a published bound
    assert {p["as_of"] for p in pts} == {"2026-07-13"} and len({p["raw_sha256"] for p in pts}) == 1


def test_wdi_the_years_not_yet_published_are_recorded_as_gaps_with_a_reason_and_never_filled(points):
    pts, gaps, _ = points
    assert len(gaps) == 12 and {g["period_start"][:4] for g in gaps} == {"2024", "2025"}
    assert all("not published" in g["reason"] and g["series_id"] == worldbank_wdi.SERIES_ID for g in gaps)
    assert not [p for p in pts if p["period_start"][:4] in ("2024", "2025")]


@pytest.mark.parametrize("mutate,match", [
    (lambda d: d[1][0].update(countryiso3code="FRA"), "unexpected area"),
    (lambda d: d[1][0].update(value=-1.0), "not a positive finite"),
    (lambda d: d[1][0]["indicator"].update(id="EN.ATM.PM25.MC.ZS"), "unexpected indicator"),
    (lambda d: d[0].pop("lastupdated"), "lastupdated"),
    (lambda d: d[1].__setitem__(slice(None), [r for r in d[1] if r["countryiso3code"] != "ZAF"]), r"no values for \['ZA'\]"),
])
def test_wdi_a_changed_response_is_a_loud_error_naming_the_source(fixture_bytes, mutate, match):
    raw, _ = fixture_bytes("worldbank", FIXTURE)
    doc = json.loads(raw)
    mutate(doc)
    with pytest.raises(SourceError, match=rf"^\[worldbank\].*{match}"):
        worldbank_wdi.parse(json.dumps(doc).encode(), "2026-10-01T00:00:00Z")


def test_wdi_an_error_message_from_the_api_and_a_mostly_empty_response_are_refused(fixture_bytes):
    with pytest.raises(SourceError, match="not the expected"):
        worldbank_wdi.parse(b'[{"message":[{"id":"120","key":"Invalid format"}]}]', "2026-10-01T00:00:00Z")
    raw, _ = fixture_bytes("worldbank", FIXTURE)
    doc = json.loads(raw)
    for r in doc[1]:
        r["value"] = None
    with pytest.raises(SourceError, match="broken response"):
        worldbank_wdi.parse(json.dumps(doc).encode(), "2026-10-01T00:00:00Z")


def test_wdi_is_registered_as_an_optional_request_with_its_fixture():
    req = next(r for r in registry.REQUESTS if r.name == "wdi_pm25")
    assert req.source == "worldbank" and req.optional and req.key_env is None and "EN.ATM.PM25.MC.M3" in req.url
    loaded = fetch.load(req, "fixture")
    assert loaded.kind == "fixture" and len(fetch.parse(loaded, [])) > 0
