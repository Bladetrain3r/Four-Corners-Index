import json

import pytest

from pipeline import eurostat
from pipeline.common import SourceError, dumps


def _points(fixture_bytes, name, dataset):
    raw, m = fixture_bytes("eurostat", name)
    return eurostat.parse(raw, dataset, m["fetched_at"]), raw


def _one(points, **want):
    hits = [p for p in points if all(p.get(k) == v for k, v in want.items())]
    assert len(hits) == 1, f"{len(hits)} matches for {want}"
    return hits[0]


def test_eurostat_household_eu27_dc_all_taxes_2025s2(fixture_bytes, series_schema):
    pts, _ = _points(fixture_bytes, "nrg_pc_204_household.json", "nrg_pc_204")
    for p in pts:
        series_schema.validate(p)
    p = _one(pts, region="EU", series_id="nrg_pc_204:KWH2500-4999:I_TAX:EUR", period_start="2025-07-01")
    assert p["value"] == 0.2896 and p["unit"] == "EUR/kWh" and p["period_end"] == "2025-12-31"
    assert p["buyer_type"] == "household" and p["layer"] == "cost"


def test_eurostat_geo_decoded_by_index_not_request_order(fixture_bytes):
    pts, _ = _points(fixture_bytes, "nrg_pc_204_household.json", "nrg_pc_204")
    # request order was EU27_2020, DE, FR...; response order is EU27_2020, DE, ES, ...
    de = _one(pts, region="DE", series_id="nrg_pc_204:KWH2500-4999:I_TAX:EUR", period_start="2025-07-01")
    fr = _one(pts, region="FR", series_id="nrg_pc_204:KWH2500-4999:I_TAX:EUR", period_start="2025-07-01")
    assert (de["value"], fr["value"]) == (0.3869, 0.2561)


def test_eurostat_industrial_x_vat_and_tax_levels_distinct(fixture_bytes):
    pts, _ = _points(fixture_bytes, "nrg_pc_205_nonhousehold.json", "nrg_pc_205")
    x = _one(pts, region="EU", series_id="nrg_pc_205:MWH2000-19999:X_VAT:EUR", period_start="2025-07-01")
    i = _one(pts, region="EU", series_id="nrg_pc_205:MWH2000-19999:I_TAX:EUR", period_start="2025-07-01")
    assert (x["value"], i["value"]) == (0.1596, 0.1920) and x["buyer_type"] == "industrial"


def test_eurostat_components_keep_code_and_do_not_pretend_to_sum(fixture_bytes):
    pts, _ = _points(fixture_bytes, "nrg_pc_204_c_components.json", "nrg_pc_204_c")
    codes = {p["component"] for p in pts}
    assert {"NRG_SUP", "NETC", "TAX_FEE_LEV_CHRG", "VAT"} <= codes
    de = _one(pts, component="NRG_SUP", period_start="2025-01-01")
    assert de["value"] == 0.1481 and de["period_end"] == "2025-12-31"


def test_eurostat_hicp_units_and_monthly_period(fixture_bytes):
    pts, _ = _points(fixture_bytes, "prc_hicp_minr_CP0451.json", "prc_hicp_minr")
    p = _one(pts, region="EU", series_id="prc_hicp_minr:CP0451:I25", period_start="2026-08-01")
    assert p["value"] == 102.58 and p["unit"] == "index 2025=100" and p["period_end"] == "2026-08-31"
    r = _one(pts, region="DE", series_id="prc_hicp_minr:CP0451:RCH_A", period_start="2026-08-01")
    assert r["value"] == -5.6 and r["unit"] == "% annual change"


def test_eurostat_consumption_gwh_and_provisional_flag(fixture_bytes):
    pts, _ = _points(fixture_bytes, "nrg_cb_e_consumption.json", "nrg_cb_e")
    p = _one(pts, region="EU", series_id="nrg_cb_e:FC:E7000", period_start="2025-01-01")
    assert abs(p["value"] - 2412055.15) < 0.01 and p["unit"] == "GWh" and p["source_flag"] == "p"


def test_eurostat_no_silent_nan_and_deterministic_output(fixture_bytes):
    pts, raw = _points(fixture_bytes, "nrg_pc_204_household.json", "nrg_pc_204")
    assert all(p["value"] == p["value"] and abs(p["value"]) != float("inf") for p in pts)
    again = eurostat.parse(raw, "nrg_pc_204", pts[0]["retrieved_at"])
    assert dumps(pts) == dumps(again)


def test_eurostat_corrupted_dimension_name_fails_naming_source(fixture_bytes):
    raw, m = fixture_bytes("eurostat", "nrg_pc_204_household.json")
    bad = raw.replace(b'"nrg_cons"', b'"consom"')
    with pytest.raises(SourceError, match=r"^\[eurostat\].*dimensions changed"):
        eurostat.parse(bad, "nrg_pc_204", m["fetched_at"])


def test_eurostat_corrupted_value_shape_fails_naming_source(fixture_bytes):
    raw, m = fixture_bytes("eurostat", "nrg_pc_204_household.json")
    doc = json.loads(raw)
    doc["value"] = list(doc["value"].values())
    with pytest.raises(SourceError, match=r"^\[eurostat\].*sparse"):
        eurostat.parse(json.dumps(doc).encode(), "nrg_pc_204", m["fetched_at"])


def test_eurostat_non_numeric_value_fails(fixture_bytes):
    raw, m = fixture_bytes("eurostat", "nrg_pc_204_household.json")
    doc = json.loads(raw)
    k = next(iter(doc["value"]))
    doc["value"][k] = "n/a"
    with pytest.raises(SourceError, match=r"^\[eurostat\].*non-numeric"):
        eurostat.parse(json.dumps(doc).encode(), "nrg_pc_204", m["fetched_at"])


def test_eurostat_wrong_unit_fails(fixture_bytes):
    raw, m = fixture_bytes("eurostat", "nrg_pc_204_household.json")
    with pytest.raises(SourceError, match=r"^\[eurostat\].*unit"):
        eurostat.parse(raw.replace(b'"KWH"', b'"MWH"'), "nrg_pc_204", m["fetched_at"])
