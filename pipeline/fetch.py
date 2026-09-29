"""Load one registry request: live over HTTP, from its fixture, or auto (live when its key is present).

A live failure raises (the SPEC says a failing source turns the run red). A missing key in `auto` mode uses the
fixture and says so in the result, never silently.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline import http
from pipeline.common import SourceError
from pipeline.registry import REQUESTS, Request, resolve_pink_sheet_url

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
UTC_NOW = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class Loaded:
    request: Request
    raw: bytes
    retrieved_at: str
    kind: str  # 'live' or 'fixture'
    url: str  # redacted
    note: str = ""


def _now() -> str:
    import time
    return time.strftime(UTC_NOW, time.gmtime())


def _fixture(req: Request, note: str) -> Loaded:
    entries = {e["file"]: e for e in json.loads((FIXTURES / req.source / "MANIFEST.json").read_text())}
    if req.fixture not in entries:
        raise SourceError(req.source, f"fixture {req.fixture} is not in its manifest")
    e = entries[req.fixture]
    return Loaded(req, (FIXTURES / req.source / req.fixture).read_bytes(), e["fetched_at"], "fixture", e["url"], note)


def load(req: Request, mode: str = "auto", *, opener: http.Opener = http._urlopen, now: Any = _now) -> Loaded:
    if mode not in ("live", "fixture", "auto"):
        raise ValueError(f"unknown mode {mode!r}")
    key = os.environ.get(req.key_env, "") if req.key_env else ""
    if mode == "fixture":
        return _fixture(req, "fixture mode")
    if req.key_env and not key:
        if mode == "auto":
            return _fixture(req, f"{req.key_env} absent: using the committed fixture, values are NOT current")
        raise SourceError(req.source, f"{req.key_env} is not set")
    url = req.url
    if url.startswith("resolve:"):
        page, _ = http.get(req.source, url.removeprefix("resolve:"), opener=opener)
        url = resolve_pink_sheet_url(page)
    fetch_url = url.replace("{key}", key)
    raw, _headers = http.get(req.source, fetch_url, opener=opener)
    return Loaded(req, raw, now(), "live", http.redact(fetch_url))


def parse(loaded: Loaded, gaps: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Publisher gaps are recorded into `gaps` when given; without it a null is a loud error."""
    return loaded.request.parse(loaded.raw, loaded.retrieved_at, loaded.kind, gaps)


def run(mode: str = "auto", only: str | None = None, include_cross_checks: bool = True) -> list[tuple[Loaded, int, int]]:
    out = []
    for req in REQUESTS:
        if only and req.source != only:
            continue
        if req.role == "cross_check" and not include_cross_checks:
            continue
        loaded = load(req, mode)
        gaps: list[dict[str, Any]] = []
        out.append((loaded, len(parse(loaded, gaps)), len(gaps)))
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Fetch and parse every registered request; prints one line each.")
    ap.add_argument("--mode", choices=("live", "fixture", "auto"), default="auto")
    ap.add_argument("--only")
    args = ap.parse_args(argv)
    failed = 0
    for req in REQUESTS:
        if args.only and req.source != args.only:
            continue
        try:
            loaded = load(req, args.mode)
            gaps: list[dict[str, Any]] = []
            n = len(parse(loaded, gaps))
            print(f"OK   {req.source:10s} {req.name:24s} {loaded.kind:8s} {n:7d} points {len(gaps):4d} gaps {len(loaded.raw):9d} bytes  {loaded.note}")
        except SourceError as exc:
            failed += 1
            print(f"FAIL {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
