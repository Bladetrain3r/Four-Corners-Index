"""Eskom: two hand-entered figures, shown on the South Africa card only, never fetched (Eskom's terms bar robots and crawlers, clause 2.10)."""

import json
from pathlib import Path

from pipeline import site_data

ROOT = Path(__file__).resolve().parent.parent
FACTS = site_data.manual("eskom_tariffs.json")


def test_nothing_the_pipeline_or_a_workflow_runs_touches_eskom():
    """The compliance guarantee: no code path can fetch from eskom.co.za. Data files may name its URLs as citations."""
    offenders = [str(p.relative_to(ROOT)) for p in list((ROOT / "pipeline").glob("*.py")) + list((ROOT / ".github" / "workflows").glob("*.yml"))
                 if "eskom" in p.read_text().lower().replace("source_id", "").replace('"eskom"', "").replace("eskom_tariffs.json", "")]
    registry_urls = [r.url for r in __import__("pipeline.registry", fromlist=["REQUESTS"]).REQUESTS]
    assert not [u for u in registry_urls if "eskom" in u.lower()]
    assert offenders == ["pipeline/site_data.py"] or offenders == [], offenders  # site_data only reads the hand-entered JSON (its ZA branch)


def test_the_two_figures_are_as_read_and_internally_consistent():
    h, i = FACTS["facts"]["household"], FACTS["facts"]["industrial"]
    assert FACTS["read"] == "2026-09-29" and h["currency"] == i["currency"] == "ZAR"
    assert h["value"] == 2.7030 and "270.30 c/kWh including 15% VAT" in h["as_published"] and "235.04" in h["as_published"]
    assert abs(235.04 * 1.15 - 270.30) < 0.01  # the VAT-inclusive figure is the excl-VAT figure plus 15%, to Eskom's rounding
    assert i["value"] == 2.1203 and "212.03" in i["as_published"] and i["period_start"] == "2025-04-01" and i["period_end"] == "2026-03-31"
    assert h["confidence"] == "low_confidence" and "municipal" in h["note"] and "not a list tariff" in i["note"]
    assert all(f["url"].startswith("https://www.eskom.co.za/") for f in (h, i))


def test_the_terms_clauses_are_recorded_verbatim_and_the_sources_entry_states_how_it_complies():
    t = FACTS["terms"]
    assert "private, personal, educational and/or non-commercial purposes only" in t["clause_2_1"] and "robots or web spiders" in t["clause_2_10"]
    src = site_data.manual("sources.json")
    used = next(s for s in src["used"] if s["id"] == "eskom")
    assert "inverted commas and acknowledged" in used["quote"] and used["licence_url"] == t["url"]
    assert "never fetched automatically" in used["modified"] and "If Eskom objects, the two figures are removed" in used["modified"] and "written consent" in used["modified"]
    assert "Eskom" in used["attribution"]
    not_used = [n for n in src["not_used"] if "Eskom" in n["name"]]
    assert len(not_used) == 1 and "clause 2.10" in not_used[0]["reason"] and "Data Portal" in not_used[0]["name"]


def test_the_south_africa_card_shows_both_figures_with_period_source_and_caveat_and_keeps_wholesale_as_no_source():
    za = next(r for r in site_data.regions_docs()[0]["regions"] if r["id"] == "ZA")
    h, i, w = za["cards"]["household"], za["cards"]["industrial"], za["cards"]["wholesale"]
    assert (h["value"], h["period_label"], h["confidence"], h["source_id"]) == (2.7030, "tariff year 2026/27", "low_confidence", "eskom")
    assert (i["value"], i["period_label"], i["confidence"]) == (2.1203, "financial year 2025/26", "primary")
    assert h["as_of"] == i["as_of"] == FACTS["read"] and h["url"].startswith("https://www.eskom.co.za/") and not h["provisional"]
    assert w["status"] == "gap" and "market" in w["reason"] and za["in_basket"] is False


def test_method_says_so_and_the_index_files_do_not_change_when_eskom_is_added():
    method = (ROOT / "METHOD.md").read_text()
    assert "Version 4" in method and "two Eskom figures" in method and "never fetched automatically" in method
    assert "(Eskom terms bar commercial reuse and crawling; Ziggy: drop)" not in method  # the old, now false, sentence is gone
    info = json.loads((ROOT / "snapshots" / "launch" / "build_info.json").read_text())
    assert info["headline_method_version"] == {"retail": 2, "wholesale": 1}  # headline definitions untouched by v4
