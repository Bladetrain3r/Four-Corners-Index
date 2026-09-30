import subprocess
from pathlib import Path

import pytest

from checks import cross_check

ROOT = Path(__file__).resolve().parent.parent
ROWS = cross_check.run()  # fixture mode: offline and reproducible

@pytest.mark.parametrize("check_id", list(cross_check.TOL["checks"]))
def test_cross_check_passes(check_id):
    rows = [r for r in ROWS if r.check == check_id and r.gating]
    if cross_check.TOL["checks"][check_id].get("gating") is False:
        assert rows == [] and [r for r in ROWS if r.check == check_id], "an information check must produce rows and none may gate"
        return
    assert rows, f"{check_id} produced no gating rows"
    bad = [f"{r.item}: ours {r.ours} theirs {r.theirs} ({r.tolerance}) {r.note}" for r in rows if not r.passed]
    assert not bad, "; ".join(bad)


def test_information_rows_keep_the_discrepancies_visible():
    ember = {r.item: r for r in ROWS if r.check == "ember_yearly_demand_vs_sum_of_monthly"}
    assert ember["US 2025"].passed and not ember["EU 2025"].passed and not ember["ZA 2025"].passed
    assert all(not r.gating for r in ember.values())
    sweep = next(r for r in ROWS if r.check == "worldbank_vs_imf_europe_gas" and not r.gating)
    assert "2023-10" in sweep.note and "2023-11" in sweep.note and not sweep.passed
    gate = next(r for r in ROWS if r.check == "worldbank_vs_imf_europe_gas" and r.gating)
    assert gate.passed and "latest 12" in gate.item


def test_sanity_ranges_hold_on_the_committed_fixtures():
    rows = [r for r in ROWS if r.check == "sanity"]
    assert len(rows) == len(cross_check.TOL["sanity_ranges"])
    assert all(r.passed for r in rows), [r.item for r in rows if not r.passed]


def test_every_tolerance_entry_is_exercised():
    assert {r.check for r in ROWS} - {"sanity"} == set(cross_check.TOL["checks"])


def test_a_tighter_tolerance_makes_a_passing_check_fail(monkeypatch):
    tol = cross_check.TOL["checks"]["eia_henry_hub_monthly_vs_daily"]
    monkeypatch.setitem(tol, "abs", 0.001)
    rows = [r for r in cross_check.eia_checks() if r.check == "eia_henry_hub_monthly_vs_daily"]
    assert rows and not rows[0].passed  # mean of daily 2.78524 vs monthly 2.78: the tolerance really bites


def test_tolerances_were_committed_before_the_runner():
    if subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, capture_output=True, text=True,
                      check=False).stdout.strip() != "false":
        pytest.skip("shallow clone: commit order not available")

    def first_commit(path: str) -> int:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ct", "--", path], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
        return int(out[-1])

    assert first_commit("checks/tolerances.yaml") <= first_commit("checks/cross_check.py")


def test_the_uk_household_all_taxes_series_used_by_the_index_matches_in_every_semester():
    rows = [r for r in ROWS if r.check == "desnz_household_vs_eurostat_uk" and r.item.startswith("incl_tax")]
    assert len(rows) == 11 and all(r.passed for r in rows)  # 2015-S1 to 2020-S1, including the last one


def test_the_two_uk_2020_s1_rows_are_information_only_and_visible():
    info = [r for r in ROWS if r.check.startswith("desnz_") and not r.gating]
    assert sorted(r.item for r in info) == ["excl_tax vs X_TAX 2020-S1", "excl_tax vs X_TAX 2020-S1", "incl_tax vs I_TAX 2020-S1", "incl_tax vs X_VAT 2020-S1"]
    outside = sorted(r.item for r in info if not r.passed)
    assert outside == ["excl_tax vs X_TAX 2020-S1", "incl_tax vs X_VAT 2020-S1"]  # the two known differences stay visible
    gating = [r for r in ROWS if r.check.startswith("desnz_") and r.gating]
    assert len(gating) == 40 and all(r.passed for r in gating)
