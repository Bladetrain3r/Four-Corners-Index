"""Deterministic writers: compact CSV series with a sidecar, daily series partitioned by month, index tables."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

SERIES_COLUMNS = ("series_id", "region", "layer", "buyer_type", "fuel", "component", "period_start", "period_end", "value", "unit",
                  "currency", "source_flag", "confidence")
DAILY_KEEP_DAYS = 730  # SPEC retention: full resolution for a rolling two years; roll-ups are kept forever


def csv_text(columns: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: ("" if r.get(c) is None else r[c]) for c in columns})
    return buf.getvalue()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def json_text(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sorted_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(points, key=lambda p: (p["series_id"], p["region"], p.get("fuel") or "", p.get("component") or "",
                                         p.get("buyer_type") or "", p["period_start"], p["value"]))


def write_series(out: Path, source: str, name: str, points: list[dict[str, Any]], meta: dict[str, Any], since: str = "2015-01-01") -> int:
    rows = sorted_points([p for p in points if p["period_end"] >= since])
    write(out / "data" / "series" / f"{source}__{name}.csv", csv_text(SERIES_COLUMNS, rows))
    write(out / "data" / "series" / f"{source}__{name}.meta.json", json_text(meta | {"rows": len(rows), "since": since}))
    return len(rows)


def write_daily(out: Path, source: str, name: str, points: list[dict[str, Any]], meta: dict[str, Any]) -> int:
    """One file per month (immutable once the month is over), keeping the last DAILY_KEEP_DAYS days before the newest point."""
    from datetime import date, timedelta
    newest = max(p["period_end"] for p in points)
    cutoff = (date.fromisoformat(newest) - timedelta(days=DAILY_KEEP_DAYS)).isoformat()
    kept = [p for p in points if p["period_end"] >= cutoff]
    by_month: dict[str, list[dict[str, Any]]] = {}
    for p in kept:
        by_month.setdefault(p["period_start"][:7], []).append(p)
    for m, pts in by_month.items():
        write(out / "data" / "series" / "daily" / f"{source}__{name}" / f"{m}.csv", csv_text(SERIES_COLUMNS, sorted_points(pts)))
    write(out / "data" / "series" / "daily" / f"{source}__{name}" / "meta.json",
          json_text(meta | {"rows": len(kept), "months": len(by_month), "keep_days": DAILY_KEEP_DAYS, "cutoff": cutoff}))
    return len(kept)
