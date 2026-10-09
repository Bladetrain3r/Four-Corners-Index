"""Generate the site's data from data/: JSON documents, downloads (every series as CSV and JSON), the method page.

    python -m pipeline.publish [--out site]

Writes site/data/*.json, site/data/method.html, site/downloads/**. None of it is committed (see .gitignore): the deploy workflow
runs this, so the repository does not grow by hundreds of kB a day. Deterministic.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

from pipeline import mdhtml, site_air, site_data
from pipeline.snapshot import MANIFEST

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HEALTH = DATA / "health.json"


def _round(x: Any) -> Any:
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def write_json(path: Path, obj: Any, compact: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_round(obj), sort_keys=True, ensure_ascii=False, separators=(",", ":") if compact else (",", ": "), indent=None if compact else 1)
    path.write_text(text + "\n", encoding="utf-8")


def _csv_to_json(src: Path, dst: Path, meta: dict[str, Any] | None) -> None:
    with src.open(encoding="utf-8", newline="") as f:
        rd = list(csv.reader(f))
    write_json(dst, {"meta": meta or {}, "columns": rd[0], "rows": rd[1:]})


def downloads(out: Path) -> list[dict[str, Any]]:
    """Every published series as CSV and JSON, the index tables, the ledger, the raw snapshot manifest."""
    items: list[dict[str, Any]] = []
    d = out / "downloads"
    if d.exists():
        shutil.rmtree(d)

    def add(group: str, rel: str, desc: str) -> None:
        p = d / rel
        items.append({"group": group, "name": rel, "path": f"downloads/{rel}", "bytes": p.stat().st_size, "description": desc})

    for f in sorted((DATA / "series").glob("*.csv")):
        if f.name == "gaps.csv":
            continue
        m = f.with_suffix(".meta.json")
        meta = json.loads(m.read_text()) if m.exists() else None
        (d / "series").mkdir(parents=True, exist_ok=True)
        shutil.copy(f, d / "series" / f.name)
        _csv_to_json(f, d / "series" / (f.stem + ".json"), meta)
        add("Series", f"series/{f.name}", f"{f.stem}: normalised series (schema/series.schema.json), CSV")
        add("Series", f"series/{f.stem}.json", f"{f.stem}: the same series as JSON with its source metadata")
    for f in sorted((DATA / "series" / "daily").glob("*/*.csv")):
        rel = f"series/daily/{f.parent.name}/{f.name}"
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, d / rel)
        _csv_to_json(f, d / rel.replace(".csv", ".json"), None)
        add("Daily series (rolling two years)", rel, f"{f.parent.name} {f.stem}: daily values, CSV")
        add("Daily series (rolling two years)", rel.replace(".csv", ".json"), f"{f.parent.name} {f.stem}: daily values, JSON")
    (d / "series").mkdir(parents=True, exist_ok=True)
    shutil.copy(DATA / "series" / "gaps.csv", d / "series" / "gaps.csv")
    add("Series", "series/gaps.csv", "Every period a publisher left empty, with the reason: shown as gaps on the site, never interpolated")
    for f in sorted((DATA / "index").glob("*.csv")):
        (d / "index").mkdir(parents=True, exist_ok=True)
        shutil.copy(f, d / "index" / f.name)
        _csv_to_json(f, d / "index" / (f.stem + ".json"), None)
        add("Indices", f"index/{f.name}", f"{f.stem}: published index table, CSV")
        add("Indices", f"index/{f.stem}.json", f"{f.stem}: the same table as JSON")
    (d / "ledger").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "ledger" / "index.jsonl", d / "ledger" / "index.jsonl")
    add("Ledger", "ledger/index.jsonl", "The hash-chained ledger of every published index value and revision (verify with ledger/verify.py)")
    shutil.copy(MANIFEST, d / "ledger" / "raw_snapshots.jsonl")
    add("Ledger", "ledger/raw_snapshots.jsonl", "Manifest of the raw source snapshots with their SHA-256")
    return items


def publish(out: Path, health: Path = HEALTH) -> dict[str, Any]:
    dd = out / "data"
    if dd.exists():
        shutil.rmtree(dd)
    info = json.loads((DATA / "index" / "build_info.json").read_text())
    index = site_data.index_doc()
    regions, detail = site_data.regions_docs()
    write_json(dd / "index.json", index)
    write_json(dd / "regions.json", regions)
    for rid, doc in detail.items():
        write_json(dd / f"region_{rid}.json", doc)
    write_json(dd / "drivers.json", site_data.drivers_doc())
    write_json(dd / "air.json", site_air.air_doc())
    src = site_data.manual("sources.json")
    write_json(dd / "sources.json", src)
    files = downloads(out)
    write_json(dd / "downloads.json", {"items": files})
    write_json(dd / "meta.json", {"method_doc_version": info["method_doc_version"], "headline_method_version": info["headline_method_version"],
                                  "inputs_sha256": info["inputs_sha256"], "published": info["published"], "snapshots": info["snapshots"],
                                  "latest": {"retail": info["retail_months"][1], "wholesale": info["wholesale_months"][1]},
                                  "disclaimer": src["disclaimer"], "sponsor": src["sponsor"],
                                  "health": json.loads(health.read_text())["sources"] if health.exists() else {}})
    body = mdhtml.convert((ROOT / "METHOD.md").read_text())
    (dd / "method.html").write_text(f'<!-- generated from METHOD.md by pipeline.publish: do not edit -->\n<article class="prose">\n{body}\n</article>\n', encoding="utf-8")
    return {"json": len(list(dd.glob("*.json"))), "downloads": len(files)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "site")
    args = ap.parse_args(argv)
    print(json.dumps(publish(args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
