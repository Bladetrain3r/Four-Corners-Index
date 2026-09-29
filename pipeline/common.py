"""Shared adapter core: one error type that names the source, point validation, deterministic JSON."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from typing import Any

REQUIRED = (
    "source", "series_id", "region", "layer", "period_start", "period_end", "value", "unit",
    "as_of", "retrieved_at", "raw_sha256", "confidence",
)
LAYERS = {"cost", "mix", "driver"}
BUYERS = {"household", "industrial", "wholesale"}
CONFIDENCE = {"primary", "low_confidence", "high_latency"}
_SHA = re.compile(r"^[0-9a-f]{64}$")


class SourceError(Exception):
    """A source failed a check. The message always starts with the source name."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def iso_date(source: str, text: str) -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise SourceError(source, f"bad date {text!r}") from exc


def validate_point(p: dict[str, Any]) -> dict[str, Any]:
    src = p.get("source") or "unknown"
    missing = [k for k in REQUIRED if p.get(k) in (None, "")]
    if missing:
        raise SourceError(src, f"point missing {missing}: {p.get('series_id')}")
    v = p["value"]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise SourceError(src, f"non-finite or non-numeric value {v!r} in {p['series_id']}")
    if p["layer"] not in LAYERS:
        raise SourceError(src, f"bad layer {p['layer']!r}")
    if p.get("buyer_type") and p["buyer_type"] not in BUYERS:
        raise SourceError(src, f"bad buyer_type {p['buyer_type']!r}")
    if p["confidence"] not in CONFIDENCE:
        raise SourceError(src, f"bad confidence {p['confidence']!r}")
    if not _SHA.match(p["raw_sha256"]):
        raise SourceError(src, "raw_sha256 is not a sha256 hex digest")
    if iso_date(src, p["period_start"]) > iso_date(src, p["period_end"]):
        raise SourceError(src, f"period_start after period_end in {p['series_id']}")
    iso_date(src, p["as_of"])
    return p


def dumps(points: list[dict[str, Any]]) -> str:
    """Deterministic serialisation (sorted keys, fixed separators, one point per line, trailing newline)."""
    return "".join(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for p in points)


def sort_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(points, key=lambda p: (p["source"], p["series_id"], p["region"], p["period_start"]))
