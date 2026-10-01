"""G7: the air quality tab's data, against the real-response fixture (the daily run adds the live series after deploy)."""

import json
from pathlib import Path

import pytest

from pipeline import fetch, outputs, publish, registry, site_air, site_data

ROOT = Path(__file__).resolve().parent.parent


def write_series_from_fixture(root: Path) -> list[dict]:
    req = next(r for r in registry.REQUESTS if r.name == "wdi_pm25")
    loaded = fetch.load(req, "fixture")
    pts = fetch.parse(loaded, [])
    meta = {"source": "worldbank", "name": "wdi_pm25", "raw_sha256": pts[0]["raw_sha256"], "retrieved_at": loaded.retrieved_at, "url": loaded.url,
            "as_of": pts[0]["as_of"], "role": "primary"}
    outputs.write_series(root, "worldbank", "wdi_pm25", pts, meta, since="1990-01-01")
    return pts


@pytest.fixture
def with_series(tmp_path, monkeypatch):
    pts = write_series_from_fixture(tmp_path)
    real_rows, real_meta = site_data.series_rows, site_data.meta
    monkeypatch.setattr(site_data, "series_rows", lambda n: outputs_rows(tmp_path, n) if n == site_air.SERIES else real_rows(n))
    monkeypatch.setattr(site_data, "meta", lambda n: json.loads((tmp_path / "data" / "series" / f"{n}.meta.json").read_text()) if n == site_air.SERIES else real_meta(n))
    return pts


def outputs_rows(root: Path, name: str):
    import csv
    return list(csv.DictReader((root / "data" / "series" / f"{name}.csv").open(encoding="utf-8")))


def test_air_doc_has_all_six_regions_with_the_published_value_year_source_and_guideline(with_series):
    d = site_air.air_doc()
    assert d["status"] == "value" and d["newest_year"] == 2023 and d["badge"] == "B"
    assert [r["id"] for r in d["regions"]] == ["EU", "US", "CN", "RU", "ZA", "GB"]
    published = {(p["region"], int(p["period_start"][:4])): p["value"] for p in with_series}
    for r in d["regions"]:
        assert r["latest"]["year"] == 2023 and r["latest"]["value"] == published[(r["id"], 2023)]
        assert r["latest"]["times_guideline"] == pytest.approx(r["latest"]["value"] / d["guideline"]["value"])
        assert [p["y"] for p in r["series"]] == sorted(p["y"] for p in r["series"]) and r["series"][0]["y"] <= 2010
        assert all(p["v"] == published[(r["id"], p["y"])] for p in r["series"])
    g = d["guideline"]
    assert g["value"] == 5 and g["url"].startswith("https://www.who.int/") and "image table" in g["verification"] and g["read"] == "2026-10-01"
    assert d["indicator"]["url"].startswith("https://data.worldbank.org/") and "CC BY-4.0" in d["indicator"]["licence_line"]
    assert d["as_of"] == "2026-07-13" and len(d["raw_sha256"]) == 64 and "2024" in d["gap_note"]


def test_the_fuel_mix_beside_each_value_is_the_same_year_and_adds_up(with_series):
    for r in site_air.air_doc()["regions"]:
        m = r["mix"]
        assert m and m["year"] == r["latest"]["year"]
        assert m["coal"] + m["gas"] + m["other_fossil"] + m["clean"] == pytest.approx(1.0, abs=1e-4)  # Ember rounds its components: the worst region-year is off by 2.9e-5, bound chosen after looking
        assert all(0 <= m[k] <= 1 for k in ("coal", "gas", "other_fossil", "clean")) and m["total_twh"] > 0


def test_annual_mix_uses_complete_years_only():
    mix = site_air.annual_mix()
    years = {y for (_r, y) in mix}
    assert 2023 in years and max(years) < 2026  # the running year has fewer than twelve months and is left out
    assert all(abs(v["coal"] + v["gas"] + v["other_fossil"] + v["clean"] - 1) < 1e-4 for v in mix.values())  # same rounding bound as above


def test_without_the_series_the_tab_says_no_data_yet_and_still_carries_its_method(monkeypatch):
    monkeypatch.setattr(site_data, "series_rows", lambda n: (_ for _ in ()).throw(FileNotFoundError(n)) if n == site_air.SERIES else [])
    d = site_air.air_doc()
    assert d["status"] == "not_yet" and "first time it runs" in d["reason"] and d["method"] and d["guideline"]["value"] == 5 and "regions" not in d


def test_publish_writes_air_json_in_either_state(tmp_path):
    publish.publish(tmp_path)
    d = json.loads((tmp_path / "data" / "air.json").read_text())
    assert d["status"] in ("value", "not_yet") and d["indicator"]["id"] == "EN.ATM.PM25.MC.M3"


def test_the_sources_page_attributes_the_pm25_series_to_the_world_bank_and_ihme_and_says_what_is_changed():
    src = next(s for s in site_data.manual("sources.json")["used"] if s["id"] == "worldbank")
    assert "EN.ATM.PM25.MC.M3" in src["datasets"] and "IHME" in src["attribution"] and "Global Burden of Disease 2023" in src["attribution"]
    assert "removed" in src["modified"] and "IHME's own terms were not readable" in src["modified"]
