"""The daily run: fetch every source on its own, keep what changed, rebuild, record source health, and say what failed.

    python -m pipeline.daily                      # what the scheduled workflow runs
    python -m pipeline.daily --dry-run            # the same, in a temporary copy: nothing in the repository changes
    python -m pipeline.daily --force-fail eia     # test flag: treat a source as failing (proves the failure path)
    python -m pipeline.daily --simulate-publication   # the 15th-of-month rule, offline, from the committed snapshots

Rules (SPEC "Update cadence" and "Source health"):
- Every source is fetched separately. A failure (unreachable, changed shape, forced) never stops the others: the run rebuilds from
  that source's last good snapshot, records the failure in data/health.json, writes an issue file naming the source, and exits 1
  so the workflow turns red and opens the issue.
- A source whose bytes did not change adds no snapshot and, with unchanged inputs, no ledger line.
- The indices publish for the previous month on the 15th: before the 15th the newest publishable month is the one before that.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from pipeline import build, fetch, http, registry, snapshot
from pipeline.common import SourceError

ROOT = Path(__file__).resolve().parent.parent
HEALTH = ROOT / "data" / "health.json"
PUBLISH_DAY = 15
PARSE_ERRORS = (SourceError, KeyError, ValueError, IndexError, TypeError)


def cap_month(today: date) -> str:
    """The newest month the indices may publish on `today`: the previous month from the 15th, the month before that until then."""
    back = 1 if today.day >= PUBLISH_DAY else 2
    n = today.year * 12 + today.month - 1 - back
    return f"{n // 12}-{n % 12 + 1:02d}"


@dataclass
class Result:
    today: str
    cap: str
    added: list[dict[str, Any]] = field(default_factory=list)
    failures: dict[str, list[str]] = field(default_factory=dict)  # source -> messages
    health: dict[str, Any] = field(default_factory=dict)
    ledger_lines_added: int = 0
    info: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failures


def _redact(text: str) -> str:
    return http.redact(text)[:300]


def fetch_all(today: date, raw_dir: Path, manifest: Path, *, mode: str = "live", loader: Callable[..., fetch.Loaded] = fetch.load,
              force_fail: Iterable[str] = ()) -> tuple[list[dict[str, Any]], dict[str, list[str]], set[str]]:
    """Fetch and parse every registered request. Returns (new manifest entries, failures by source, sources that fetched fine)."""
    forced = set(force_fail)
    latest = {(e["source"], e["name"]): e for e in snapshot.read_manifest(manifest)}
    added: list[dict[str, Any]] = []
    failures: dict[str, list[str]] = {}
    seen, bad = set(), set()
    for req in registry.REQUESTS:
        seen.add(req.source)
        try:
            if req.source in forced:
                raise SourceError(req.source, "forced failure (test flag --force-fail)")
            loaded = loader(req, mode)
            try:
                fetch.parse(loaded, [])  # a source that changed shape fails here, before anything is stored
            except PARSE_ERRORS as e:
                raise SourceError(req.source, f"{req.name}: the response no longer parses ({type(e).__name__}: {e})") from e
            entry = snapshot.record(loaded, raw_dir, latest)
        except SourceError as e:
            bad.add(req.source)
            failures.setdefault(req.source, []).append(_redact(f"{req.name}: {e}"))
            continue
        if entry:
            added.append(entry)
    snapshot.append_manifest(manifest, added)
    return added, failures, seen - bad


def health_doc(previous: dict[str, Any], today: date, failures: dict[str, list[str]], ok: set[str]) -> dict[str, Any]:
    """Per source: status, the last date it fetched and parsed fine, and (when failing) since when and why. Dates only, so an
    unchanged run gives an unchanged file."""
    prev = previous.get("sources", {})
    out: dict[str, Any] = {}
    for src in sorted(set(prev) | ok | set(failures)):
        p = prev.get(src, {})
        if src in failures:
            out[src] = {"status": "failed", "last_good": p.get("last_good"), "failing_since": p.get("failing_since") or today.isoformat(),
                        "message": failures[src][0]}
        else:
            out[src] = {"status": "ok", "last_good": today.isoformat()}
    return {"sources": out}


def issue_text(res: Result) -> tuple[str, str]:
    names = sorted(res.failures)
    title = f"Source failing: {', '.join(names)}"
    lines = [f"The daily run of {res.today} could not fetch or parse {len(names)} source(s). The site keeps showing each source's last good data and date.", ""]
    for src in names:
        h = res.health["sources"][src]
        lines += [f"### {src}", f"- last good: {h.get('last_good') or 'no earlier good run recorded'}", f"- failing since: {h['failing_since']}"]
        lines += [f"- {m}" for m in res.failures[src]] + [""]
    lines += ["Check: `python -m pipeline.fetch --only <source>`. Nothing was published from the failing source's new data."]
    return title, "\n".join(lines)


def run(today: date, *, raw_dir: Path = snapshot.RAW, manifest: Path = snapshot.MANIFEST, out: Path = ROOT, health_path: Path = HEALTH,
        mode: str = "live", loader: Callable[..., fetch.Loaded] = fetch.load, force_fail: Iterable[str] = (), rebuild: bool = True) -> Result:
    cap = cap_month(today)
    res = Result(today.isoformat(), cap)
    res.added, res.failures, ok = fetch_all(today, raw_dir, manifest, mode=mode, loader=loader, force_fail=force_fail)
    previous = json.loads(health_path.read_text()) if health_path.exists() else {}
    res.health = health_doc(previous, today, res.failures, ok)
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text(json.dumps(res.health, indent=1, sort_keys=True) + "\n")
    if not rebuild:  # tests of the fetch and health rules only
        return res
    res.info = build.build(raw_dir, out, manifest, ledger_seed=out / "ledger" / "index.jsonl", published=today.isoformat(), max_month=cap)
    res.ledger_lines_added = res.info["_added"]
    return res


def _shift(month: str, k: int) -> str:
    n = int(month[:4]) * 12 + int(month[5:]) - 1 + k
    return f"{n // 12}-{n % 12 + 1:02d}"


def simulate_publication(work: Path, raw_dir: Path = snapshot.RAW, manifest: Path = snapshot.MANIFEST) -> dict[str, Any]:
    """The 15th arrives. From the committed snapshots: publish through the month before the newest one (as on its own 15th), then
    extend that ledger by the newest month on the simulated 15th. Nothing is fetched, nothing in the repository changes, and no
    number is invented: the newest month's inputs are the ones already in the snapshots."""
    newest = build.build(raw_dir, work / "full", manifest)["retail_months"][1]
    before = _shift(newest, -1)
    nxt = _shift(newest, 1)
    sim = date(int(nxt[:4]), int(nxt[5:]), PUBLISH_DAY)
    earlier = date(int(newest[:4]), int(newest[5:]), PUBLISH_DAY)
    assert cap_month(sim) == newest and cap_month(sim.replace(day=PUBLISH_DAY - 1)) == before and cap_month(earlier) == before
    first = build.build(raw_dir, work / "a", manifest, ledger_seed=work / "none", published=earlier.isoformat(), max_month=before)
    seed_path = work / "a" / "ledger" / "index.jsonl"
    seed_lines = seed_path.read_text().splitlines()
    second = build.build(raw_dir, work / "b", manifest, ledger_seed=seed_path, published=sim.isoformat(), max_month=cap_month(sim))
    path = work / "b" / "ledger" / "index.jsonl"
    lines = path.read_text().splitlines()
    verify = subprocess.run([sys.executable, str(ROOT / "ledger" / "verify.py"), str(path)], capture_output=True, text=True, check=False)
    return {"before_month": before, "published_month": newest, "simulated_date": sim.isoformat(),
            "lines_before": first["ledger_lines"], "lines_after": second["ledger_lines"], "earlier_lines_untouched": lines[:len(seed_lines)] == seed_lines,
            "appended": [{k: json.loads(ln)[k] for k in ("index", "month", "status", "value_usd_per_kwh", "published")} for ln in lines[len(seed_lines):]],
            "verifier_exit": verify.returncode, "verifier_output": (verify.stdout or verify.stderr).strip().splitlines()[-1]}


def finish(res: Result, issue_file: Path | None, dry_run: bool) -> int:
    """Print the outcome; on a failing source write the issue file and return 1 so the workflow turns red."""
    print(json.dumps({"today": res.today, "publishable_through": res.cap, "new_snapshots": [f"{e['source']}/{e['name']}" for e in res.added],
                      "failing_sources": res.failures, "ledger_lines_added": res.ledger_lines_added}, indent=1))
    if res.ok:
        return 0
    title, body = issue_text(res)
    if issue_file:
        issue_file.write_text(f"{title}\n\n{body}\n")
    print(("WOULD OPEN ISSUE (dry run): " if dry_run else "OPEN ISSUE: ") + title)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", type=date.fromisoformat, default=None, help="override the date (default: today, UTC)")
    ap.add_argument("--mode", choices=("live", "fixture"), default="live")
    ap.add_argument("--dry-run", action="store_true", help="work in a temporary copy of the manifest, ledger and health file; change nothing in the repository")
    ap.add_argument("--force-fail", action="append", default=[], metavar="SOURCE", help="treat this source as failing (test flag)")
    ap.add_argument("--issue-file", type=Path, help="write the issue title and body here when a source fails")
    ap.add_argument("--simulate-publication", action="store_true")
    args = ap.parse_args(argv)
    if args.simulate_publication:
        with tempfile.TemporaryDirectory() as tmp:
            print(json.dumps(simulate_publication(Path(tmp)), indent=1))
        return 0
    from datetime import UTC, datetime
    today = args.today or datetime.now(UTC).date()
    kwargs: dict[str, Any] = {}
    tmp = None
    if args.dry_run:
        tmp = Path(tempfile.mkdtemp(prefix="fci-dry-"))
        (tmp / "data" / "manifests").mkdir(parents=True)
        shutil.copy(snapshot.MANIFEST, tmp / "data" / "manifests" / "raw_snapshots.jsonl")
        if HEALTH.exists():
            shutil.copy(HEALTH, tmp / "data" / "health.json")
        (tmp / "ledger").mkdir()
        shutil.copy(ROOT / "ledger" / "index.jsonl", tmp / "ledger" / "index.jsonl")
        kwargs = {"manifest": tmp / "data" / "manifests" / "raw_snapshots.jsonl", "out": tmp, "health_path": tmp / "data" / "health.json",
                  "raw_dir": tmp / "raw_cache"}
        shutil.copytree(snapshot.RAW, kwargs["raw_dir"])
    res = run(today, mode=args.mode, force_fail=args.force_fail, **kwargs)
    code = finish(res, args.issue_file, args.dry_run)
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
