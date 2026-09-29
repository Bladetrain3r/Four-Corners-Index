import subprocess
from pathlib import Path

import pytest

from checks import cross_check

ROOT = Path(__file__).resolve().parent.parent
ROWS = cross_check.run()  # fixture mode: offline and reproducible

# Checks that are red for real, documented reasons and wait for the owner's word (reports/BLOCKED-G3.md).
# strict xfail: they show as xfailed in every run, and CI fails if one turns green without this list being updated.
OPEN = {
    "ember_yearly_demand_vs_sum_of_monthly": "publisher inconsistency, see reports/BLOCKED-G3.md item B",
    "worldbank_vs_imf_europe_gas": "two months of autumn 2023 differ by more than the tolerance, see reports/BLOCKED-G3.md item C",
}


def _params() -> list:
    out = []
    for cid in cross_check.TOL["checks"]:
        marks = [pytest.mark.xfail(strict=True, reason=OPEN[cid])] if cid in OPEN else []
        out.append(pytest.param(cid, id=cid, marks=marks))
    return out


@pytest.mark.parametrize("check_id", _params())
def test_cross_check_passes(check_id):
    rows = [r for r in ROWS if r.check == check_id]
    assert rows, f"{check_id} produced no rows"
    bad = [f"{r.item}: ours {r.ours} theirs {r.theirs} ({r.tolerance}) {r.note}" for r in rows if not r.passed]
    assert not bad, "; ".join(bad)


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
