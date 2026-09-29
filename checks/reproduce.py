"""G4 reproducibility: two clean rebuilds from the raw snapshots, with the network blocked, must be byte-identical
to each other and to the committed outputs.

    python -m checks.reproduce [--raw raw_cache]
"""
from __future__ import annotations

import argparse
import hashlib
import socket
import sys
import tempfile
from pathlib import Path

from pipeline import build

ROOT = Path(__file__).resolve().parent.parent
TREES = ("data/index", "data/series", "ledger/index.jsonl")  # generated outputs only (ledger/verify.py is hand-written)


class NetworkBlocked(RuntimeError):
    pass


def _deny(*_a, **_k):
    raise NetworkBlocked("a network connection was attempted during an offline rebuild")


def hashes(root: Path) -> dict[str, str]:
    out = {}
    for t in TREES:
        path = root / t
        for f in sorted(path.rglob("*")) if path.is_dir() else [path]:
            if f.is_file():
                out[str(f.relative_to(root))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "raw_cache")
    args = ap.parse_args(argv)
    real_connect, real_cc = socket.socket.connect, socket.create_connection
    socket.socket.connect, socket.create_connection = _deny, _deny  # type: ignore[method-assign,assignment]
    try:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            build.build(args.raw, Path(a))
            build.build(args.raw, Path(b))
            ha, hb, hc = hashes(Path(a)), hashes(Path(b)), hashes(ROOT)
    finally:
        socket.socket.connect, socket.create_connection = real_connect, real_cc  # type: ignore[method-assign]
    same_ab = ha == hb
    same_repo = ha == hc
    print(f"files per rebuild: {len(ha)}; network connections attempted: 0 (any attempt raises)")
    print(f"rebuild 1 == rebuild 2 (all {len(ha)} files byte-identical): {same_ab}")
    print(f"rebuild == committed outputs: {same_repo}")
    for k in sorted(set(ha) | set(hc)):
        if ha.get(k) != hc.get(k):
            print("  differs from committed:", k)
    for k in ("ledger/index.jsonl", "data/index/retail.csv", "data/index/wholesale.csv"):
        print(f"  {k}  sha256 {ha[k]}")
    return 0 if same_ab and same_repo else 1


if __name__ == "__main__":
    sys.exit(main())
