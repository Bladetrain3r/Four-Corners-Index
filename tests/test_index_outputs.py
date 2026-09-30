"""Invariants on the committed index outputs (produced by python -m pipeline.build from the raw snapshots)."""
import csv
import re
from decimal import Decimal as D
from itertools import pairwise
from pathlib import Path

import pytest

from checks import explain_moves
from pipeline import index as ix
from pipeline import ledger

ROOT = Path(__file__).resolve().parent.parent
IDX = ROOT / "data" / "index"


def _rows(name):
    return list(csv.DictReader((IDX / name).open()))


@pytest.fixture(scope="module")
def retail():
    return _rows("retail.csv")


@pytest.fixture(scope="module")
def wholesale():
    return _rows("wholesale.csv")


@pytest.mark.parametrize("name,regions", [("retail", ("EU", "US", "CN", "GB")), ("wholesale", ("EU",))])
def test_months_contiguous_from_2015_01_and_levels_positive(name, regions):
    rows = _rows(f"{name}.csv")
    assert [r["month"] for r in rows] == ix.months("2015-01", rows[-1]["month"])
    assert all(D(r["level_usd_per_kwh"]) > 0 and r["status"] in ("provisional", "final") for r in rows)


@pytest.mark.parametrize("name,regions", [("retail", ("EU", "US", "CN", "GB")), ("wholesale", ("EU",))])
def test_weights_sum_to_one_and_contributions_sum_to_level(name, regions):
    for r in _rows(f"{name}.csv"):
        assert abs(sum(D(r[f"weight_{g}"]) for g in regions) - 1) < D("0.000000001")
        assert abs(sum(D(r[f"contrib_{g}"]) for g in regions) - D(r["level_usd_per_kwh"])) <= D("0.000002"), r["month"]


@pytest.mark.parametrize("name", ["retail", "wholesale"])
def test_2015_averages_to_100_in_both_weightings(name):
    rows = [r for r in _rows(f"{name}.csv") if r["month"].startswith("2015-")]
    assert len(rows) == 12
    for col in ("index_2015_100", "equal_index_2015_100"):
        assert abs(sum(D(r[col]) for r in rows) / 12 - 100) < D("0.01"), col


def test_final_never_follows_provisional(retail, wholesale):
    for rows in (retail, wholesale):
        seq = [r["status"] for r in rows]
        assert seq == sorted(seq, key=lambda s: s == "provisional"), "a final month appears after a provisional one"
    assert retail[-1]["status"] == "provisional"  # EU household is carried forward for 2026


def test_retail_composition_is_eu_us_china_uk_and_excludes_russia(retail):
    assert {r["composition"] for r in retail} == {"CN|EU|GB|US"}
    weights = _rows("weights.csv")
    ru = [w for w in weights if w["region"] == "RU"]
    assert ru and all(w["share_retail_renormalised"] == "" and D(w["share_of_four"]) > 0 for w in ru)  # in the denominator, not priced


def test_weights_table_shares_sum_to_one_per_year():
    by_year: dict[str, D] = {}
    for w in _rows("weights.csv"):
        by_year[w["year"]] = by_year.get(w["year"], D(0)) + D(w["share_of_four"])
    assert all(abs(v - 1) < D("0.000000001") for v in by_year.values()) and "2026" in by_year


def test_region_prices_are_local_value_times_fx():
    for r in _rows("region_prices.csv"):
        if r["local_unit"] == "EUR/MWh":
            expect = D(r["local_value"]) * D(r["usd_per_local"])
        else:
            expect = D(r["local_value"]) * D(r["usd_per_local"])
        assert abs(expect - D(r["usd_per_kwh"])) <= D("0.00001"), (r["index"], r["month"], r["region"])


def test_eu_household_is_carried_after_the_last_published_semester():
    eu = {r["month"]: r for r in _rows("region_prices.csv") if r["index"] == "retail" and r["region"] == "EU"}
    assert eu["2025-12"]["carried"] == "0" and eu["2026-01"]["carried"] == "1" and eu["2026-01"]["provisional"] == "1"
    assert eu["2015-06"]["provisional"] == "0"


def test_wholesale_never_publishes_a_partial_month_as_final(wholesale):
    assert wholesale[-1]["month"] <= "2026-08"


def test_ledger_chain_is_intact_and_latest_lines_match_the_tables(retail, wholesale):
    lines = ledger.loads((ROOT / "ledger" / "index.jsonl").read_text())
    assert ledger.verify(lines) == []
    cur = ledger.latest(lines)
    for name, rows, version in (("retail", retail, 2), ("wholesale", wholesale, 1)):
        for r in rows:
            e = cur[(name, r["month"])]
            assert e["value_usd_per_kwh"] == r["level_usd_per_kwh"] and e["status"] == r["status"]
            assert e["index_2015_100"] == r["index_2015_100"] and e["method_version"] == version


def test_the_uk_revision_is_new_superseding_lines_and_the_v1_lines_are_untouched(retail, wholesale):
    lines = ledger.loads((ROOT / "ledger" / "index.jsonl").read_text())
    v1 = [ln for ln in lines if ln["method_version"] == 1]
    v2 = [ln for ln in lines if ln["method_version"] == 2]
    assert len(v1) == len(retail) + len(wholesale) and len(v2) == len(retail)  # wholesale was not revised
    assert all(ln["index"] == "retail" and "supersedes" in ln and ln["composition"] == ["CN", "EU", "GB", "US"] for ln in v2)
    by_hash = {ln["hash"]: ln for ln in lines}
    assert all(by_hash[ln["supersedes"]]["index"] == "retail" and by_hash[ln["supersedes"]]["month"] == ln["month"]
               and by_hash[ln["supersedes"]]["method_version"] == 1 and by_hash[ln["supersedes"]]["composition"] == ["CN", "EU", "US"] for ln in v2)
    assert all(ln.get("backfill") is True for ln in v1) and "backfill" not in v2[0]


def test_method_thresholds_match_the_code_and_every_big_move_is_explained():
    method = (ROOT / "METHOD.md").read_text()
    m = re.search(r"above \*\*(\d+)% \(Retail\)\*\* or \*\*(\d+)% \(Wholesale\)\*\*", method)
    assert m and explain_moves.THRESHOLD == {"retail": int(m.group(1)) / 100, "wholesale": int(m.group(2)) / 100}
    text, unexplained, _ = explain_moves.render()
    assert text == explain_moves.OUT.read_text(), "explained_moves.md is stale: python -m checks.explain_moves"
    assert unexplained == []
    wmonths = [r["month"] for r in _rows("wholesale.csv")]
    lv = {r["month"]: float(r["level_usd_per_kwh"]) for r in _rows("wholesale.csv")}
    big = [b for a, b in pairwise(wmonths) if abs(lv[b] / lv[a] - 1) > 0.20]
    assert big and all(f"**{b}** wholesale" in text for b in big)


def test_method_md_was_committed_before_any_index_code():
    import subprocess
    if subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, capture_output=True, text=True,
                      check=False).stdout.strip() != "false":
        pytest.skip("shallow clone")

    def first(path):
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ct", "--", path], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.split()
        return int(out[-1]) if out else 2**62  # not committed yet: necessarily after METHOD.md
    for later in ("pipeline/index.py", "pipeline/build.py", "data/index/retail.csv", "data/index/wholesale.csv", "ledger/index.jsonl"):
        assert first("METHOD.md") <= first(later), later


def test_retail_excluding_china_is_recomputed_independently_for_every_month(retail):
    w = {}
    for r in _rows("weights.csv"):
        w[(r["year"], r["region"])] = D(r["share_of_four"])  # share of the five basket regions
    usd = {(r["month"], r["region"]): D(r["usd_per_kwh"]) for r in _rows("region_prices.csv") if r["index"] == "retail"}
    for r in retail:
        y, m = r["month"][:4], r["month"]
        regs = ("EU", "US", "GB")
        expect = sum(w[(y, g)] * usd[(m, g)] for g in regs) / sum(w[(y, g)] for g in regs)
        assert abs(expect - D(r["exchina_level_usd_per_kwh"])) <= D("0.000001"), m
        contrib = sum(D(r[f"exchina_contrib_{g}"]) for g in regs)
        assert abs(contrib - D(r["exchina_level_usd_per_kwh"])) <= D("0.000003"), m


def test_ex_china_index_averages_100_in_2015_and_is_not_a_ledger_series(retail):
    rows = [r for r in retail if r["month"].startswith("2015-")]
    assert abs(sum(D(r["exchina_index_2015_100"]) for r in rows) / 12 - 100) < D("0.01")
    assert {ln["index"] for ln in ledger.loads((ROOT / "ledger" / "index.jsonl").read_text())} == {"retail", "wholesale"}
    assert D(retail[-1]["exchina_index_2015_100"]) > D(retail[-1]["index_2015_100"])  # the measured part rose more than the headline
