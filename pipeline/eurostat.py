"""Eurostat adapter: JSON-stat 2.0 responses (nrg_pc_204, nrg_pc_205, nrg_pc_204_c, prc_hicp_minr, nrg_cb_e).

Every dataset is decoded by the dimension `index` maps, never by request order (Eurostat returns
geos in its own order) and `value` is a sparse object keyed by the flat row-major index.
"""
from __future__ import annotations

import calendar
import json
from datetime import date
from typing import Any

from pipeline.common import SourceError, sha256_hex, validate_point

SOURCE = "eurostat"

REGION = {"EU27_2020": "EU", "EU": "EU", "EA": "EA"}
PRICE_DIMS = {"freq", "siec", "nrg_cons", "unit", "tax", "currency", "geo", "time"}
# dataset -> (required dimensions, layer, buyer_type)
DATASETS: dict[str, tuple[set[str], str, str | None]] = {
    "nrg_pc_204": (PRICE_DIMS, "cost", "household"),
    "nrg_pc_205": (PRICE_DIMS, "cost", "industrial"),
    "nrg_pc_204_c": ({"freq", "nrg_cons", "nrg_prc", "currency", "geo", "time"}, "cost", "household"),
    "prc_hicp_minr": ({"freq", "unit", "coicop18", "geo", "time"}, "cost", "household"),
    "nrg_cb_e": ({"freq", "nrg_bal", "siec", "unit", "geo", "time"}, "mix", None),
}


def period_bounds(label: str) -> tuple[date, date]:
    """'2025-S2' -> Jul 1..Dec 31; '2026-08' -> the month; '2025' -> the year."""
    try:
        if "-S" in label:
            year, half = label.split("-S")
            y, h = int(year), int(half)
            if h not in (1, 2):
                raise ValueError
            return (date(y, 1, 1), date(y, 6, 30)) if h == 1 else (date(y, 7, 1), date(y, 12, 31))
        if len(label) == 7:
            y, m = int(label[:4]), int(label[5:])
            return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
        if len(label) == 4:
            y = int(label)
            return date(y, 1, 1), date(y, 12, 31)
    except ValueError:
        pass
    raise SourceError(SOURCE, f"unrecognised period label {label!r}")


def decode(raw: bytes, dataset: str) -> list[tuple[dict[str, str], float, str | None]]:
    """Return (coordinates, value, flag) for every observation present. Fails loudly on shape changes."""
    if dataset not in DATASETS:
        raise SourceError(SOURCE, f"unknown dataset {dataset!r}")
    try:
        doc = json.loads(raw)
        ids, sizes = doc["id"], doc["size"]
        dims = doc["dimension"]
        values = doc["value"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError(SOURCE, f"{dataset}: not a JSON-stat dataset ({exc!r})") from exc
    expected = DATASETS[dataset][0]
    if set(ids) != expected:
        raise SourceError(SOURCE, f"{dataset}: dimensions changed, got {sorted(ids)}, expected {sorted(expected)}")
    if not isinstance(values, dict):
        raise SourceError(SOURCE, f"{dataset}: `value` is not the sparse object form")
    flags = doc.get("status") or {}
    labels: list[dict[int, str]] = []
    for d in ids:
        idx = dims[d]["category"]["index"]
        if isinstance(idx, list):
            idx = {code: i for i, code in enumerate(idx)}
        labels.append({pos: code for code, pos in idx.items()})
    strides = [1] * len(ids)
    for i in range(len(ids) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    out = []
    for key, val in values.items():
        flat = int(key)
        coords = {}
        for d, lab, stride, size in zip(ids, labels, strides, sizes, strict=True):
            coords[d] = lab[(flat // stride) % size]
        if val is None or not isinstance(val, (int, float)) or isinstance(val, bool):
            raise SourceError(SOURCE, f"{dataset}: non-numeric value {val!r} at {coords}")
        out.append((coords, float(val), flags.get(key)))
    if not out:
        raise SourceError(SOURCE, f"{dataset}: response holds no observations")
    return out


def parse(raw: bytes, dataset: str, retrieved_at: str, confidence: str = "primary") -> list[dict[str, Any]]:
    _, layer, buyer = DATASETS[dataset]
    updated = json.loads(raw).get("updated", "")[:10]
    if not updated:
        raise SourceError(SOURCE, f"{dataset}: response has no `updated` date")
    digest = sha256_hex(raw)
    points = []
    for c, value, flag in decode(raw, dataset):
        start, end = period_bounds(c["time"])
        p: dict[str, Any] = {
            "source": SOURCE, "region": REGION.get(c["geo"], c["geo"]), "layer": layer,
            "period_start": start.isoformat(), "period_end": end.isoformat(), "value": value,
            "as_of": updated, "retrieved_at": retrieved_at, "raw_sha256": digest, "confidence": confidence,
        }
        if buyer:
            p["buyer_type"] = buyer
        if flag:
            p["source_flag"] = flag
        if dataset in ("nrg_pc_204", "nrg_pc_205"):
            p["series_id"] = f"{dataset}:{c['nrg_cons']}:{c['tax']}:{c['currency']}"
            if c["unit"] != "KWH":
                raise SourceError(SOURCE, f"{dataset}: unit {c['unit']!r}, expected KWH")
            p["unit"] = f"{c['currency']}/kWh"
            p["currency"] = c["currency"]
        elif dataset == "nrg_pc_204_c":
            p["series_id"] = f"{dataset}:{c['nrg_cons']}:{c['currency']}"
            p["component"] = c["nrg_prc"]
            p["unit"] = f"{c['currency']}/kWh"
            p["currency"] = c["currency"]
        elif dataset == "prc_hicp_minr":
            p["series_id"] = f"{dataset}:{c['coicop18']}:{c['unit']}"
            p["unit"] = {"I25": "index 2025=100", "I15": "index 2015=100", "RCH_A": "% annual change",
                         "RCH_M": "% monthly change"}.get(c["unit"], c["unit"])
        else:  # nrg_cb_e
            if c["unit"] != "GWH":
                raise SourceError(SOURCE, f"{dataset}: unit {c['unit']!r}, expected GWH")
            p["series_id"] = f"{dataset}:{c['nrg_bal']}:{c['siec']}"
            p["unit"] = "GWh"
        points.append(validate_point(p))
    return points
