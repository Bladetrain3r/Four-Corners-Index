"""Verify every fixtures/<source>/MANIFEST.json: files exist, sha256 matches, url + fetched_at present,
no API key material, and no fixture over the size budget. Usage: verify_fixtures.py [--root DIR]."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REQUIRED = ("file", "url", "fetched_at", "sha256", "note", "source_kind")
MAX_BYTES = 300_000
KEY_PARAM = re.compile(r"(api_key|token|apikey|securityToken)=(?!REDACTED)[^&\s]+", re.IGNORECASE)


def check_source(src_dir: Path) -> list[str]:
    errors: list[str] = []
    mpath = src_dir / "MANIFEST.json"
    if not mpath.exists():
        return [f"{src_dir.name}: no MANIFEST.json (need one, or a NO_SOURCE.md)"] if not (
            src_dir / "NO_SOURCE.md").exists() else []
    entries = json.loads(mpath.read_text())
    listed = set()
    for e in entries:
        missing = [k for k in REQUIRED if not e.get(k)]
        if missing:
            errors.append(f"{src_dir.name}/{e.get('file', '?')}: manifest missing {missing}")
            continue
        listed.add(e["file"])
        f = src_dir / e["file"]
        if not f.is_file():
            errors.append(f"{src_dir.name}/{e['file']}: listed but missing")
            continue
        if hashlib.sha256(f.read_bytes()).hexdigest() != e["sha256"]:
            errors.append(f"{src_dir.name}/{e['file']}: sha256 mismatch")
        if f.stat().st_size > MAX_BYTES:
            errors.append(f"{src_dir.name}/{e['file']}: {f.stat().st_size} bytes exceeds {MAX_BYTES}")
        if KEY_PARAM.search(e["url"]):
            errors.append(f"{src_dir.name}/{e['file']}: url carries a key-like parameter")
    for f in src_dir.iterdir():
        if f.name not in listed and f.name not in ("MANIFEST.json", "NO_SOURCE.md", "README.md"):
            errors.append(f"{src_dir.name}/{f.name}: file not in manifest")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("fixtures"))
    args = ap.parse_args(argv)
    errors: list[str] = []
    n = 0
    for d in sorted(p for p in args.root.iterdir() if p.is_dir()):
        errors += check_source(d)
        n += 1
    secret = os.environ.get("EIA_API_KEY") or os.environ.get("ENTSOE_TOKEN")
    if secret and len(secret) > 8:
        for f in args.root.rglob("*"):
            if f.is_file() and secret.encode() in f.read_bytes():
                errors.append(f"{f}: contains a secret from the environment (redacted)")
    for e in errors:
        print("FAIL", e)
    print(f"{n} fixture dirs checked, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
