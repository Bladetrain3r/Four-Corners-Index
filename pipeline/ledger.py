"""Hash-chained ledger of published index values (METHOD.md section 7). Standard library only.

Each line: the entry plus `prev_hash` (the previous line's `hash`, or GENESIS) and `hash` = SHA-256 of the canonical JSON of the
entry without `hash`. Canonical JSON: sorted keys, separators ',' and ':', UTF-8, no ASCII escaping. A revision is a new line
that names the hash it supersedes; earlier lines are never edited.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

GENESIS = "GENESIS"
VALUE_KEYS = ("index", "month", "value_usd_per_kwh", "index_2015_100", "status", "composition", "method_version")


def canonical(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_hash(entry_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(entry_without_hash).encode("utf-8")).hexdigest()


def dumps(lines: list[dict[str, Any]]) -> str:
    return "".join(canonical(line) + "\n" for line in lines)


def loads(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def latest(lines: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for ln in lines:
        out[(ln["index"], ln["month"])] = ln
    return out


def append(existing: list[dict[str, Any]], values: list[dict[str, Any]], published: str, inputs_sha256: str,
           backfill: bool = False) -> list[dict[str, Any]]:
    """Lines to add for `values` (dicts with VALUE_KEYS). Unchanged values add nothing; changed ones supersede."""
    current = latest(existing)
    prev = existing[-1]["hash"] if existing else GENESIS
    added: list[dict[str, Any]] = []
    for v in sorted(values, key=lambda x: (x["index"], x["month"])):
        old = current.get((v["index"], v["month"]))
        if old and all(old[k] == v[k] for k in VALUE_KEYS):
            continue
        entry: dict[str, Any] = {k: v[k] for k in VALUE_KEYS} | {"published": published, "inputs_sha256": inputs_sha256}
        if backfill:
            entry["backfill"] = True
        if old:
            entry["supersedes"] = old["hash"]
        entry["prev_hash"] = prev
        entry["hash"] = entry_hash(entry)
        prev = entry["hash"]
        added.append(entry)
    return added


def verify(lines: list[dict[str, Any]]) -> list[str]:
    """Empty list if the chain is intact; otherwise one message per problem."""
    errors = []
    prev = GENESIS
    seen: dict[str, int] = {}
    for i, ln in enumerate(lines, start=1):
        if ln.get("prev_hash") != prev:
            errors.append(f"line {i}: prev_hash {str(ln.get('prev_hash'))[:12]} does not match the previous line's hash {prev[:12]}")
        body = {k: v for k, v in ln.items() if k != "hash"}
        if entry_hash(body) != ln.get("hash"):
            errors.append(f"line {i}: hash does not match the line's content (edited?)")
        sup = ln.get("supersedes")
        if sup is not None and sup not in seen:
            errors.append(f"line {i}: supersedes a hash that is not an earlier line")
        seen[ln.get("hash", "")] = i
        prev = ln.get("hash", "")
    return errors
