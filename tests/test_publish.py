import csv
import hashlib
import json
from pathlib import Path

import pytest

from pipeline import mdhtml, publish

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    publish.publish(out)
    return out


def _j(site, name):
    return json.loads((site / "data" / name).read_text())


def test_index_json_matches_the_csv_tables(site):
    idx = _j(site, "index.json")
    rows = list(csv.DictReader((ROOT / "data" / "index" / "retail.csv").open()))
    assert len(idx["retail"]) == len(rows) and idx["retail"][-1]["m"] == rows[-1]["month"]
    assert abs(idx["retail"][-1]["level"] - float(rows[-1]["level_usd_per_kwh"])) < 1e-9
    assert abs(idx["retail"][-1]["ex_level"] - float(rows[-1]["exchina_level_usd_per_kwh"])) < 1e-9
    assert len(idx["wholesale"]) == len(list(csv.DictReader((ROOT / "data" / "index" / "wholesale.csv").open())))
    assert all(r["published"] and r["method_version"] in (1, 2) for r in idx["retail"] + idx["wholesale"])
    assert len(idx["revisions"]) == 140 and all(r["method_version"] == 2 for r in idx["revisions"])
    assert idx["ledger"]["lines"] == 420 and len(idx["ledger"]["head"]) == 64


def test_fx_covers_every_index_month_with_the_currencies_the_toggle_needs(site):
    idx = _j(site, "index.json")
    for r in idx["retail"] + idx["wholesale"]:
        fx = idx["fx"][r["m"]]
        assert {"USD", "ZAR", "GBP", "CNY"} <= set(fx) and all(v > 0 for v in fx.values())


def test_every_region_card_has_a_value_or_a_reason_and_as_of_source_badge(site):
    regs = _j(site, "regions.json")["regions"]
    assert [r["id"] for r in regs] == ["EU", "US", "CN", "RU", "ZA", "GB"]
    for r in regs:
        assert r["badge"] in ("A", "B", "C") and r["badge_note"]
        assert set(r["cards"]) == {"household", "industrial", "wholesale"}
        for kind, c in r["cards"].items():
            if c["status"] == "value":
                assert c["value"] > 0 and c["currency"] and c["as_of"] and c["source"] and c["period_end"] and c["source_id"], (r["id"], kind)
                assert c["confidence"] in ("primary", "low_confidence", "high_latency")
            else:
                assert c["status"] == "gap" and len(c["reason"]) > 20, (r["id"], kind)


def test_the_known_gaps_are_present_with_their_reasons(site):
    regs = {r["id"]: r for r in _j(site, "regions.json")["regions"]}
    assert regs["US"]["cards"]["wholesale"]["status"] == "gap" and "ICE" in regs["US"]["cards"]["wholesale"]["reason"]
    assert all(regs["RU"]["cards"][k]["status"] == "gap" for k in ("household", "industrial", "wholesale"))
    assert "Eskom" in regs["ZA"]["cards"]["household"]["reason"] and "market" in regs["ZA"]["cards"]["wholesale"]["reason"]
    assert "sterling" in regs["GB"]["cards"]["wholesale"]["reason"]
    assert regs["CN"]["cards"]["household"]["confidence"] == "low_confidence" and regs["CN"]["badge"] == "C"
    assert regs["EU"]["cards"]["household"]["value"] == pytest.approx(0.2896) and regs["GB"]["cards"]["household"]["value"] == pytest.approx(0.297773, abs=1e-6)


def test_mix_shares_sum_to_one_and_carbon_and_dates_are_present(site):
    for r in _j(site, "regions.json")["regions"]:
        mix = r["mix"]
        assert abs(sum(mix["shares"].values()) - 1) < 0.002, r["id"]
        assert mix["carbon"] > 0 and mix["total_twh"] > 0 and mix["as_of"] and mix["source"]
        assert len(mix["fuels"]) == 8  # at most the eight validated palette slots
    assert {r["id"]: r["mix"]["confidence"] for r in _j(site, "regions.json")["regions"]}["RU"] == "low_confidence"


def test_region_detail_files_have_series_mix_over_time_and_sources(site):
    for rid in ("EU", "US", "CN", "RU", "ZA", "GB"):
        d = _j(site, f"region_{rid}.json")
        assert d["sources"] and d["mix_over_time"] and d["gaps"] is not None
        for s in d["series"].values():
            assert s["points"] and s["currency"] and s["unit"]
    assert set(_j(site, "region_EU.json")["series"]) >= {"household", "industrial", "industrial_comparison", "wholesale"}
    assert _j(site, "region_ZA.json")["series"] == {} and len(_j(site, "region_ZA.json")["gaps"]) == 3


def test_eu_price_components_are_published_with_their_reconciliation_to_the_half_year_prices(site):
    comp = _j(site, "region_EU.json")["components"]
    assert len(comp["years"]) >= 7 and "not explained" in comp["note"]
    rec = {r["year"]: r for r in comp["reconciliation"]}
    assert len(rec) >= 5
    for y in comp["years"]:
        total = y["energy_supply"] + y["network"] + y["other_taxes_levies"] + y["vat"]
        if y["year"] in rec:
            assert abs(rec[y["year"]]["components_total"] - total) < 1e-9
            # measured: the annual components differ from the half-year mean by -0.9% to +2.3% (largest in 2021 and 2023); 3% is the
            # bound chosen after looking at those numbers, to catch a broken decomposition, not to certify the publisher's data
            assert abs(rec[y["year"]]["difference"]) / rec[y["year"]]["half_year_mean"] < 0.03, y["year"]
    assert abs(rec["2025"]["difference"]) < 0.001  # the latest year reconciles closely


def test_drivers_have_twelve_month_sparklines_and_the_two_omissions_are_explained(site):
    items = {i["id"]: i for i in _j(site, "drivers.json")["items"]}
    values = [i for i in items.values() if i["status"] == "value"]
    assert len(values) == 8 and all(len(i["series"]) == 13 and i["as_of"] and i["source"] and i["badge"] == "A" for i in values)
    assert items["ttf"]["latest"]["v"] == 21.11 and items["ttf"]["change_12m"] == pytest.approx(0.893, abs=0.001)
    assert items["carbon"]["status"] == "gap" and "no free" in items["carbon"]["reason"]
    assert items["rub"]["status"] == "gap" and "rightsholders" in items["rub"]["reason"]


def test_every_download_exists_with_the_recorded_size_and_series_come_as_csv_and_json(site):
    items = _j(site, "downloads.json")["items"]
    assert len(items) > 100
    for it in items:
        p = site / it["path"]
        assert p.is_file() and p.stat().st_size == it["bytes"], it["path"]
    names = {it["name"] for it in items}
    for f in (ROOT / "data" / "series").glob("*.csv"):
        if f.name != "gaps.csv":
            assert f"series/{f.name}" in names and f"series/{f.stem}.json" in names
    assert "ledger/raw_snapshots.jsonl" in names and "ledger/index.jsonl" in names
    j = json.loads((site / "downloads" / "series" / "eurostat__nrg_pc_204.json").read_text())
    assert j["columns"][0] == "series_id" and j["meta"]["source"] == "eurostat" and len(j["rows"]) > 1000


def test_the_ledger_and_manifest_downloads_are_byte_copies(site):
    for rel, src in (("ledger/index.jsonl", ROOT / "ledger" / "index.jsonl"), ("ledger/raw_snapshots.jsonl", ROOT / "data" / "manifests" / "raw_snapshots.jsonl")):
        assert hashlib.sha256((site / "downloads" / rel).read_bytes()).hexdigest() == hashlib.sha256(src.read_bytes()).hexdigest()


def test_publish_is_deterministic(site, tmp_path):
    publish.publish(tmp_path)
    for p in sorted((site / "data").glob("*.json")) + [site / "data" / "method.html"]:
        assert p.read_bytes() == (tmp_path / p.relative_to(site)).read_bytes(), p.name
    a = sorted(str(p.relative_to(site)) for p in (site / "downloads").rglob("*") if p.is_file())
    b = sorted(str(p.relative_to(tmp_path)) for p in (tmp_path / "downloads").rglob("*") if p.is_file())
    assert a == b


def test_sources_json_has_attribution_for_every_source_shown(site):
    src = _j(site, "sources.json")
    used = {s["id"] for s in src["used"]}
    shown = {c["source_id"] for r in _j(site, "regions.json")["regions"] for c in r["cards"].values() if c["status"] == "value"}
    shown |= {i["source_id"] for i in _j(site, "drivers.json")["items"] if i["status"] == "value"} | {"ember"}
    assert shown <= used, shown - used
    assert all(s["attribution"] and s["licence"] and s["licence_url"] for s in src["used"]) and src["sponsor"]["url"].endswith("Bladetrain3r")
    assert "no paywall" in src["sponsor"]["line"] and len(src["not_used"]) >= 7


def test_method_page_is_generated_from_method_md_and_escapes_markup(site):
    html = (site / "data" / "method.html").read_text()
    assert "<h1" in html and "Method" in html and "Retail excluding China" in html and "<table>" in html
    assert "<script" not in html


def test_markdown_converter_handles_the_constructs_and_escapes():
    out = mdhtml.convert("# T\n\nA **bold** and *it* and `code` <b>x</b> [l](https://a.b/c).\n\n- one\n- two\n\n1. a\n2. b\n\n| h1 | h2 |\n|---|---|\n| x | y |\n\n> quote")
    assert "<h1 id=\"t\">T</h1>" in out and "<strong>bold</strong>" in out and "<em>it</em>" in out and "<code>code</code>" in out
    assert "&lt;b&gt;x&lt;/b&gt;" in out and '<a href="https://a.b/c">l</a>' in out
    assert out.count("<li>") == 4 and "<th>h1</th>" in out and "<td>y</td>" in out and "<blockquote>" in out
