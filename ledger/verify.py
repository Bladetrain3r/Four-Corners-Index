"""Verify ledger/index.jsonl. Standalone: standard library only, no repo imports, so anyone can run it.

    python ledger/verify.py [path]      exit 0 if the hash chain is intact, 1 otherwise
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

GENESIS = "GENESIS"
REQUIRED = ("index", "month", "value_usd_per_kwh", "index_2015_100", "status", "composition", "method_version", "published",
            "inputs_sha256", "prev_hash", "hash")


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def check(text: str) -> list[str]:
    errors = []
    prev = GENESIS
    seen = set()
    n = 0
    for i, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        n += 1
        try:
            ln = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {i}: not valid JSON ({exc})")
            continue
        missing = [k for k in REQUIRED if k not in ln]
        if missing:
            errors.append(f"line {i}: missing {missing}")
            continue
        if ln["status"] not in ("provisional", "final") or ln["index"] not in ("retail", "wholesale"):
            errors.append(f"line {i}: bad index or status")
        if not re.match(r"^-?[0-9]+\.[0-9]{6}$", str(ln["value_usd_per_kwh"])):
            errors.append(f"line {i}: value is not a six-decimal string")
        if ln["prev_hash"] != prev:
            errors.append(f"line {i}: prev_hash does not match the previous line's hash")
        body = {k: v for k, v in ln.items() if k != "hash"}
        if hashlib.sha256(canonical(body).encode("utf-8")).hexdigest() != ln["hash"]:
            errors.append(f"line {i}: hash does not match the content (line edited?)")
        if "supersedes" in ln and ln["supersedes"] not in seen:
            errors.append(f"line {i}: supersedes a hash that is not an earlier line")
        seen.add(ln["hash"])
        prev = ln["hash"]
    if n == 0:
        errors.append("ledger is empty")
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent / "index.jsonl"
    errors = check(path.read_text())
    for e in errors:
        print("FAIL", e)
    lines = sum(1 for ln in path.read_text().splitlines() if ln.strip())
    print(f"{path.name}: {lines} lines, {len(errors)} problems" + ("" if errors else ", chain intact"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
