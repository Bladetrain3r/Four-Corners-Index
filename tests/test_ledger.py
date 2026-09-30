import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from pipeline import ledger

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "index.schema.json").read_text())
SHA = "a" * 64


def _v(month="2015-01", value="0.131250", status="final", index="retail"):
    return {"index": index, "month": month, "value_usd_per_kwh": value, "index_2015_100": "100.000", "status": status,
            "composition": ["CN", "EU", "US"], "method_version": 1}


def _chain(n=3):
    return ledger.append([], [_v(f"2015-{m:02d}") for m in range(1, n + 1)], "2026-09-30", SHA, backfill=True)


def test_chain_starts_at_genesis_links_and_validates_against_the_schema():
    lines = _chain()
    assert lines[0]["prev_hash"] == ledger.GENESIS and lines[1]["prev_hash"] == lines[0]["hash"]
    for ln in lines:
        jsonschema.validate(ln, SCHEMA)
    assert ledger.verify(lines) == []


def test_tampering_with_a_value_fails_verification():
    lines = _chain()
    lines[1]["value_usd_per_kwh"] = "9.999999"
    errs = ledger.verify(lines)
    assert errs and "line 2" in errs[0] and "hash does not match" in errs[0]


def test_rehashing_a_tampered_line_still_breaks_the_next_link():
    lines = _chain()
    lines[0]["value_usd_per_kwh"] = "9.999999"
    body = {k: v for k, v in lines[0].items() if k != "hash"}
    lines[0]["hash"] = ledger.entry_hash(body)  # an attacker who fixes the hash of the edited line...
    errs = ledger.verify(lines)
    assert any("line 2" in e and "prev_hash" in e for e in errs)  # ...still breaks the chain at the next line


def test_deleting_or_reordering_lines_fails():
    lines = _chain()
    assert ledger.verify([lines[0], lines[2]])
    assert ledger.verify([lines[1], lines[0], lines[2]])


def test_unchanged_values_add_nothing_and_a_change_is_a_new_superseding_line():
    lines = _chain()
    assert ledger.append(lines, [_v("2015-01")], "2026-10-15", SHA) == []
    rev = ledger.append(lines, [_v("2015-01", value="0.140000", status="final")], "2026-10-15", SHA)
    assert len(rev) == 1 and rev[0]["supersedes"] == lines[0]["hash"] and rev[0]["prev_hash"] == lines[-1]["hash"]
    full = lines + rev
    assert ledger.verify(full) == [] and ledger.latest(full)[("retail", "2015-01")]["value_usd_per_kwh"] == "0.140000"
    assert full[0]["value_usd_per_kwh"] == "0.131250"  # the superseded line is untouched


def test_provisional_to_final_is_a_revision():
    lines = ledger.append([], [_v("2026-01", status="provisional")], "2026-02-15", SHA)
    rev = ledger.append(lines, [_v("2026-01", status="final")], "2026-08-15", SHA)
    assert len(rev) == 1 and rev[0]["status"] == "final" and "supersedes" in rev[0]


def test_standalone_verifier_agrees_and_fails_on_tampering(tmp_path):
    good = tmp_path / "good.jsonl"
    good.write_text(ledger.dumps(_chain()))
    ok = subprocess.run([sys.executable, str(ROOT / "ledger" / "verify.py"), str(good)], capture_output=True, text=True, check=False)
    assert ok.returncode == 0 and "chain intact" in ok.stdout
    bad = tmp_path / "bad.jsonl"
    bad.write_text(good.read_text().replace('"0.131250"', '"0.999999"', 1))
    r = subprocess.run([sys.executable, str(ROOT / "ledger" / "verify.py"), str(bad)], capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "FAIL" in r.stdout
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    assert subprocess.run([sys.executable, str(ROOT / "ledger" / "verify.py"), str(empty)], capture_output=True, check=False).returncode == 1
