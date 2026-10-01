"""G6: the daily run's rules, offline. The 'live' source is the committed snapshot archive, so nothing touches the network."""

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from pipeline import daily, fetch, ledger, publish, snapshot

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 30)
LAUNCH = ROOT / "snapshots" / "launch"  # manifest and ledger at the state of the committed archive; the daily job moves the live ones


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("raw")
    snapshot.restore(ROOT / "snapshots" / "raw_2026-09-29.tar.gz", d, LAUNCH / "manifest.jsonl")
    return d


@pytest.fixture
def work(raw_dir, tmp_path):
    """A private copy of the manifest and ledger; the raw files are shared and read-only (no test here adds a snapshot)."""
    w = tmp_path
    (w / "data" / "manifests").mkdir(parents=True)
    (w / "ledger").mkdir()
    shutil.copy(LAUNCH / "manifest.jsonl", w / "data" / "manifests" / "raw_snapshots.jsonl")
    shutil.copy(LAUNCH / "ledger.jsonl", w / "ledger" / "index.jsonl")
    (w / "raw").symlink_to(raw_dir, target_is_directory=True)
    return w


@pytest.fixture
def no_parse(monkeypatch):
    """For tests of the health rules only: skip parsing every response (the parse check has its own test)."""
    monkeypatch.setattr(fetch, "parse", lambda loaded, gaps=None: [])


def serving(work, garbage=(), raising=None):
    """A loader that answers each request with the committed snapshot bytes as if fetched live now (garbage: request names that return junk)."""
    snaps = snapshot.load_snapshots(work / "raw", work / "data" / "manifests" / "raw_snapshots.jsonl")

    def loader(req, mode):
        if raising and req.source == raising[0]:
            raise raising[1]
        if (req.source, req.name) in snaps:
            entry, raw = snaps[(req.source, req.name)]
            url = entry["url"]
        else:  # a request added after launch: its first fetch (the fixture's bytes stand in for the live response)
            fx = fetch.load(req, "fixture")
            raw, url = fx.raw, fx.url
        return fetch.Loaded(req, b"<html>maintenance</html>" if req.name in garbage else raw, "2026-09-30T04:00:00Z", "live", url)

    return loader


def go(work, **kw):
    kw.setdefault("rebuild", False)
    return daily.run(TODAY, raw_dir=work / "raw", manifest=work / "data" / "manifests" / "raw_snapshots.jsonl", out=work,
                     health_path=work / "data" / "health.json", **kw)


def test_the_fifteenth_rule_publishes_the_previous_month_from_the_15th_only():
    assert daily.cap_month(date(2026, 10, 14)) == "2026-08" and daily.cap_month(date(2026, 10, 15)) == "2026-09"
    assert daily.cap_month(date(2027, 1, 14)) == "2026-11" and daily.cap_month(date(2027, 1, 15)) == "2026-12"
    assert daily.cap_month(date(2027, 2, 1)) == "2026-12" and daily.cap_month(date(2027, 3, 31)) == "2027-02"


def test_a_run_where_nothing_changed_adds_no_ledger_line_and_only_the_first_snapshot_of_a_new_request(work):
    r = go(work, loader=serving(work), rebuild=True)
    assert [f"{e['source']}/{e['name']}" for e in r.added] == ["worldbank/wdi_pm25"]  # the one request launch did not have: its first snapshot
    assert [e["name"] for e in snapshot.read_manifest(work / "data" / "manifests" / "raw_snapshots.jsonl")].count("wdi_pm25") == 1
    assert go(work, loader=serving(work), rebuild=False).added == []  # and then nothing is new
    assert r.ok and r.ledger_lines_added == 0 and r.cap == "2026-08"
    assert (work / "ledger" / "index.jsonl").read_bytes() == (LAUNCH / "ledger.jsonl").read_bytes()
    health = json.loads((work / "data" / "health.json").read_text())["sources"]
    assert set(health) == {"desnz", "ecb", "eia", "ember", "eurostat", "worldbank"} and all(h == {"status": "ok", "last_good": "2026-09-30"} for h in health.values())
    first = (work / "data" / "health.json").read_bytes()
    go(work, loader=serving(work))
    assert (work / "data" / "health.json").read_bytes() == first  # no churn between identical runs


def test_a_forced_source_failure_turns_the_run_red_names_the_source_and_keeps_the_others_going(work, tmp_path, capsys):
    r = go(work, loader=serving(work), force_fail=["eia"], rebuild=True)
    assert not r.ok and list(r.failures) == ["eia"] and r.info["ledger_lines"] == 420  # rebuilt from eia's last good snapshot
    h = r.health["sources"]
    assert h["eia"]["status"] == "failed" and h["eia"]["failing_since"] == "2026-09-30" and "forced failure" in h["eia"]["message"]
    assert all(v["status"] == "ok" for k, v in h.items() if k != "eia")
    issue = tmp_path / "issue.md"
    assert daily.finish(r, issue, dry_run=True) == 1
    text = issue.read_text()
    assert text.startswith("Source failing: eia") and "### eia" in text and "failing since: 2026-09-30" in text
    assert "WOULD OPEN ISSUE (dry run): Source failing: eia" in capsys.readouterr().out
    assert daily.finish(go(work, loader=serving(work)), None, dry_run=False) == 0


def test_a_failure_keeps_the_last_good_date_and_a_recovery_clears_it(work, no_parse):
    go(work, loader=serving(work))
    r = daily.run(date(2026, 10, 2), rebuild=False, raw_dir=work / "raw", manifest=work / "data" / "manifests" / "raw_snapshots.jsonl", out=work,
                  health_path=work / "data" / "health.json", loader=serving(work), force_fail=["ember"])
    e = r.health["sources"]["ember"]
    assert e == {"status": "failed", "last_good": "2026-09-30", "failing_since": "2026-10-02", "message": e["message"]}
    r = daily.run(date(2026, 10, 3), rebuild=False, raw_dir=work / "raw", manifest=work / "data" / "manifests" / "raw_snapshots.jsonl", out=work,
                  health_path=work / "data" / "health.json", loader=serving(work), force_fail=["ember"])
    assert r.health["sources"]["ember"]["failing_since"] == "2026-10-02" and r.health["sources"]["ember"]["last_good"] == "2026-09-30"
    r = daily.run(date(2026, 10, 4), rebuild=False, raw_dir=work / "raw", manifest=work / "data" / "manifests" / "raw_snapshots.jsonl", out=work,
                  health_path=work / "data" / "health.json", loader=serving(work))
    assert r.health["sources"]["ember"] == {"status": "ok", "last_good": "2026-10-04"}


def test_a_source_that_changed_shape_fails_and_its_junk_is_never_stored(work):
    before = len(snapshot.read_manifest(work / "data" / "manifests" / "raw_snapshots.jsonl"))
    r = go(work, loader=serving(work, garbage={"nrg_pc_204"}))
    assert list(r.failures) == ["eurostat"] and "no longer parses" in r.failures["eurostat"][0]
    manifest = snapshot.read_manifest(work / "data" / "manifests" / "raw_snapshots.jsonl")
    assert [e["sha256"] for e in manifest if e["name"] == "nrg_pc_204"] == [e["sha256"] for e in snapshot.read_manifest(LAUNCH / "manifest.jsonl") if e["name"] == "nrg_pc_204"]
    assert len(manifest) == before + 1 and [e["name"] for e in r.added] == ["wdi_pm25"]  # the junk was refused; only the new request's first snapshot was kept


def test_a_key_in_an_error_message_is_redacted_before_it_reaches_health_or_the_issue(work, no_parse):
    from pipeline.common import SourceError
    err = SourceError("eia", "GET https://api.eia.gov/v2/x?api_key=SUPERSECRETKEY123 returned 500")
    r = go(work, loader=serving(work, raising=("eia", err)))
    blob = json.dumps(r.health) + daily.issue_text(r)[1]
    assert "SUPERSECRETKEY123" not in blob and "api_key=REDACTED" in blob


def test_the_site_shows_a_failing_source_with_its_last_good_date(work, no_parse, tmp_path):
    r = go(work, loader=serving(work), force_fail=["eia"])
    out = tmp_path / "site"
    publish.publish(out, health=work / "data" / "health.json")
    meta = json.loads((out / "data" / "meta.json").read_text())
    assert meta["health"]["eia"]["status"] == "failed" and meta["health"]["eia"]["last_good"] is None
    assert meta["health"]["ecb"] == {"status": "ok", "last_good": "2026-09-30"} and r.health["sources"]["eia"]["failing_since"]


def test_simulated_fifteenth_appends_one_line_per_index_and_the_verifier_passes(tmp_path, raw_dir):
    s = daily.simulate_publication(tmp_path, raw_dir, LAUNCH / "manifest.jsonl")
    assert s["published_month"] == "2026-08" and s["simulated_date"] == "2026-09-15" and s["lines_after"] == s["lines_before"] + 2
    assert [(a["index"], a["month"], a["published"]) for a in s["appended"]] == [("retail", "2026-08", "2026-09-15"), ("wholesale", "2026-08", "2026-09-15")]
    assert {a["status"] for a in s["appended"]} == {"provisional", "final"} and s["earlier_lines_untouched"] and s["verifier_exit"] == 0
    assert "0 problems, chain intact" in s["verifier_output"]
    # the appended values are the launch ledger's own newest values: nothing was invented
    committed = {(ln["index"], ln["month"]): ln for ln in ledger.loads((LAUNCH / "ledger.jsonl").read_text())}
    for a in s["appended"]:
        assert committed[(a["index"], a["month"])]["value_usd_per_kwh"] == a["value_usd_per_kwh"]


def test_an_unexpected_error_in_one_source_is_that_sources_failure_and_the_others_still_run(work, no_parse):
    """A bug or a freak network error in one adapter must not end the run before the health file and the issue are written."""
    r = go(work, loader=serving(work, raising=("ember", RuntimeError("boom with api_key=SECRETSECRET1"))))
    assert list(r.failures) == ["ember"] and "unexpected RuntimeError" in r.failures["ember"][0] and "SECRETSECRET1" not in r.failures["ember"][0]
    assert all(v["status"] == "ok" for k, v in r.health["sources"].items() if k != "ember")
