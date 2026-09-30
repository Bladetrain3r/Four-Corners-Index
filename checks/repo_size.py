"""Fail if tracked files exceed the size budget (default 200 MB). Usage: repo_size.py [--limit-mb N]."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def tracked_bytes(root: Path) -> int:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    ).stdout.decode()
    total = 0
    for name in filter(None, out.split("\0")):
        p = root / name
        if p.is_file():
            total += p.stat().st_size
    return total


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-mb", type=float, default=200.0)
    ap.add_argument("--root", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    size = tracked_bytes(args.root)
    limit = int(args.limit_mb * 1024 * 1024)
    verdict = "OK" if size <= limit else "FAIL"
    print(f"tracked {size / 1024 / 1024:.2f} MB, limit {args.limit_mb:g} MB: {verdict}")
    return 0 if size <= limit else 1


if __name__ == "__main__":
    sys.exit(main())
