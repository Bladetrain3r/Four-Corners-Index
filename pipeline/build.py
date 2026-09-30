"""Offline build: raw snapshots (verified against the manifest) -> series files, the two indices, weights, ledger.

    python -m pipeline.build [--raw raw_cache] [--out .]

No network. Same snapshots in, byte-identical files out. METHOD.md v1 is the specification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from typing import Any

from pipeline import index as ix
from pipeline import ledger, outputs, registry, snapshot
from pipeline.common import SourceError

ROOT = Path(__file__).resolve().parent.parent
HEADLINE_METHOD_VERSION = {"retail": 2, "wholesale": 1}  # the ledger's method_version per index: the headline definition (METHOD.md v3 added the UK to Retail)
METHOD_DOC_VERSION = 3
BASKET = ("EU", "US", "CN", "RU", "GB")
RETAIL_REGIONS = ("EU", "US", "CN", "GB")  # RU has no price (METHOD section 1)
EXCHINA_REGIONS = ("EU", "US", "GB")  # the regions with measured prices
DAILY = {"henry_hub_daily", "prices_daily", "exr_daily"}
CARRY_EU, CARRY_US = 12, 3  # METHOD section 6
EIA_PROVISIONAL_MONTHS = 12
EU_SERIES = "nrg_pc_204:KWH2500-4999:I_TAX:EUR"


def _parse_all(raw_dir: Path, manifest: Path) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    snaps = snapshot.load_snapshots(raw_dir, manifest)
    missing = [(r.source, r.name) for r in registry.REQUESTS if (r.source, r.name) not in snaps]
    if missing:
        raise SourceError("build", f"no raw snapshot for {missing}; run python -m pipeline.snapshot")
    points: dict[tuple[str, str], list[dict[str, Any]]] = {}
    gaps: list[dict[str, Any]] = []
    meta: dict[tuple[str, str], dict[str, Any]] = {}
    for req in registry.REQUESTS:
        entry, raw = snaps[(req.source, req.name)]
        g: list[dict[str, Any]] = []
        points[(req.source, req.name)] = req.parse(raw, entry["retrieved_at"], "live", g)
        gaps += g
        meta[(req.source, req.name)] = entry
    return points, gaps, meta


def _dec_series(pts: list[dict[str, Any]], series_id: str, region: str, **extra: Any) -> dict[str, D]:
    out: dict[str, D] = {}
    for p in pts:
        if p["series_id"] == series_id and p["region"] == region and all(p.get(k) == v for k, v in extra.items()):
            ix.expand_period(p["period_start"], p["period_end"], ix.dec(p["value"]), out)
    return out


def _fx(points: dict[tuple[str, str], list[dict[str, Any]]]) -> tuple[dict[str, D], dict[str, D], dict[str, D]]:
    pts = points[("ecb", "exr_monthly")]
    return tuple(_dec_series(pts, f"ecb:EXR:M:{c}:EUR", c) for c in ("USD", "CNY", "GBP"))  # type: ignore[return-value]


def _demand(points: dict[tuple[str, str], list[dict[str, Any]]]) -> dict[tuple[str, int], D]:
    out: dict[tuple[str, int], D] = {}
    for p in points[("ember", "yearly_generation")]:
        if p["fuel"] == "demand" and p["series_id"] == "ember:yearly:generation":
            out[(p["region"], int(p["period_start"][:4]))] = ix.dec(p["value"])
    return out


def _china(manual: Path) -> tuple[D, str]:
    s = next(x for x in json.loads(manual.read_text())["series"] if x["in_index"])
    return ix.dec(s["value"]), s["valid_from"][:7]


def build_retail(points, fx_usd, fx_cny, fx_gbp, demand, snap_date: date, manual: Path, last_month: str):
    eu_obs = _dec_series(points[("eurostat", "nrg_pc_204")], EU_SERIES, "EU")
    us_obs = _dec_series(points[("eia", "retail_price")], "electricity/retail-sales:price:RES", "US")
    uk_obs = _dec_series(points[("desnz", "qep_562")], "desnz:qep_5.6.2:medium:incl_tax", "GB")
    cn_value, cn_from = _china(manual)
    all_months = ix.months("2015-01", last_month)
    eu = ix.carry_forward(eu_obs, all_months, CARRY_EU)
    us = ix.carry_forward(us_obs, all_months, CARRY_US)
    uk = ix.carry_forward(uk_obs, all_months, CARRY_EU)  # semi-annual like the EU series
    cutoff = date(snap_date.year - 1, snap_date.month, min(snap_date.day, 28))
    rows, region_rows = [], []
    levels_w, levels_e, levels_x = {}, {}, {}
    for m in all_months:
        if m not in fx_usd or m not in fx_cny or m not in fx_gbp or m not in eu or m not in us or m not in uk or m < cn_from:
            continue
        y = int(m[:4])
        usd_per_eur = fx_usd[m]
        usd_per_cny = usd_per_eur / fx_cny[m]
        usd_per_gbp = usd_per_eur / fx_gbp[m]
        us_prov = us[m][1] or ix.month_end(m) > cutoff
        parts = {
            "EU": ix.RegionMonth("EU", m, eu[m][0], "EUR/kWh", usd_per_eur, ix.q6(eu[m][0] * usd_per_eur), eu[m][1], eu[m][1]),
            "US": ix.RegionMonth("US", m, us[m][0], "USD/kWh", D(1), ix.q6(us[m][0]), us[m][1], us_prov),
            "CN": ix.RegionMonth("CN", m, cn_value, "CNY/kWh", usd_per_cny, ix.q6(cn_value * usd_per_cny), False, False),
            "GB": ix.RegionMonth("GB", m, uk[m][0], "GBP/kWh", usd_per_gbp, ix.q6(uk[m][0] * usd_per_gbp), uk[m][1], uk[m][1]),
        }
        base = ix.demand_shares(demand, BASKET, y)
        usd = {r: p.usd for r, p in parts.items()}
        c = ix.combine(m, usd, base)
        e = ix.combine(m, usd, base, equal=True)
        x = ix.combine(m, {r: usd[r] for r in EXCHINA_REGIONS}, base)  # variant: China dropped, weights renormalised over EU, US and the UK
        prov = any(p.provisional for p in parts.values())
        levels_w[m], levels_e[m], levels_x[m] = c.level, e.level, x.level
        rows.append({"month": m, "status": "provisional" if prov else "final", "level": c.level, "equal_level": e.level,
                     "composition": "|".join(c.composition), "contrib": c.contributions, "weights": c.weights,
                     "exchina_level": x.level, "exchina_contrib": x.contributions})
        for r, p in sorted(parts.items()):
            region_rows.append({"index": "retail", "month": m, "region": r, "local_value": p.local_value, "local_unit": p.local_unit,
                                "usd_per_local": p.usd_per_local.quantize(D("0.00000001")), "usd_per_kwh": p.usd,
                                "carried": int(p.carried), "provisional": int(p.provisional)})
    idx_w, idx_e, idx_x = ix.index_form(levels_w), ix.index_form(levels_e), ix.index_form(levels_x)
    for r in rows:
        r["index"], r["equal_index"], r["exchina_index"] = idx_w[r["month"]], idx_e[r["month"]], idx_x[r["month"]]
    return rows, region_rows


def build_wholesale(points, fx_usd, snap_date: date, id_by_country: dict[tuple[str, int], D], last_month: str):
    eu27 = set(registry.EU27)
    price: dict[str, dict[str, D]] = {}
    for p in points[("ember", "prices_monthly")]:
        if p["region"] in eu27 and p["series_id"] == "ember:monthly:day_ahead_price":
            price.setdefault(p["period_start"][:7], {})[p["region"]] = ix.dec(p["value"])
    rows, region_rows, comp_rows = [], [], []
    levels = {}
    for m in ix.months("2015-01", last_month):
        if m not in fx_usd or m not in price or ix.month_end(m) >= snap_date:  # the current month of Ember's file is partial
            continue
        y = int(m[:4])
        weights = {c: v for (c, yr), v in id_by_country.items() if yr == y - 1}
        mean_eur_mwh, w = ix.weighted_mean(price[m], weights)
        usd = ix.q6(mean_eur_mwh / 1000 * fx_usd[m])
        covered = sum((weights[c] for c in w), D(0)) / sum(weights.values())
        c = ix.combine(m, {"EU": usd}, {"EU": D(1)})
        levels[m] = c.level
        rows.append({"month": m, "status": "final", "level": c.level, "equal_level": c.level, "composition": "EU",
                     "contrib": c.contributions, "weights": c.weights})
        region_rows.append({"index": "wholesale", "month": m, "region": "EU", "local_value": ix.q6(mean_eur_mwh), "local_unit": "EUR/MWh",
                            "usd_per_local": (fx_usd[m] / 1000).quantize(D("0.00000001")), "usd_per_kwh": usd, "carried": 0, "provisional": 0})
        comp_rows.append({"month": m, "n_countries": len(w), "share_of_eu_inland_demand": covered.quantize(D("0.0001")),
                          "countries": "|".join(sorted(w))})
    idx = ix.index_form(levels)
    for r in rows:
        r["index"], r["equal_index"] = idx[r["month"]], idx[r["month"]]
    return rows, region_rows, comp_rows


def _index_csv(rows: list[dict[str, Any]], regions: tuple[str, ...]) -> str:
    has_x = "exchina_level" in rows[0]
    cols = ("month", "status", "level_usd_per_kwh", "index_2015_100", "equal_level_usd_per_kwh", "equal_index_2015_100", "composition") + tuple(
        f"contrib_{r}" for r in regions) + tuple(f"weight_{r}" for r in regions) + (
        ("exchina_level_usd_per_kwh", "exchina_index_2015_100") + tuple(f"exchina_contrib_{r}" for r in EXCHINA_REGIONS) if has_x else ())
    flat = []
    for r in rows:
        d = {"month": r["month"], "status": r["status"], "level_usd_per_kwh": r["level"], "index_2015_100": r["index"],
             "equal_level_usd_per_kwh": r["equal_level"], "equal_index_2015_100": r["equal_index"], "composition": r["composition"]}
        for reg in regions:
            d[f"contrib_{reg}"] = r["contrib"].get(reg, "")
            d[f"weight_{reg}"] = r["weights"].get(reg, "")
        if has_x:
            d |= {"exchina_level_usd_per_kwh": r["exchina_level"], "exchina_index_2015_100": r["exchina_index"]}
            d |= {f"exchina_contrib_{reg}": r["exchina_contrib"][reg] for reg in EXCHINA_REGIONS}
        flat.append(d)
    return outputs.csv_text(cols, flat)


def build(raw_dir: Path, out: Path, manifest: Path = snapshot.MANIFEST, manual: Path = ROOT / "data" / "manual" / "china_household_tariff.json",
          ledger_seed: Path | None = None, published: str | None = None) -> dict[str, Any]:
    """`ledger_seed`: an existing ledger to extend (append-only): only values that changed become new, superseding lines."""
    points, gaps, meta = _parse_all(raw_dir, manifest)
    snap_date = date.fromisoformat(max(e["retrieved_at"] for e in meta.values())[:10])
    fx_usd, fx_cny, fx_gbp = _fx(points)
    demand = _demand(points)
    id_by_country = {(p["region"], int(p["period_start"][:4])): ix.dec(p["value"]) for p in points[("eurostat", "nrg_cb_e")]
                     if p["series_id"] == "nrg_cb_e:ID:E7000" and p["region"] in registry.EU27}
    last_fx = min(max(fx_usd), max(fx_cny), max(fx_gbp))
    retail, retail_regions = build_retail(points, fx_usd, fx_cny, fx_gbp, demand, snap_date, manual, last_fx)
    wholesale, wholesale_regions, comp = build_wholesale(points, fx_usd, snap_date, id_by_country, last_fx)
    # series files
    counts = {}
    for (source, name), pts in points.items():
        m = {"source": source, "name": name, "raw_sha256": meta[(source, name)]["sha256"], "retrieved_at": meta[(source, name)]["retrieved_at"],
             "url": meta[(source, name)]["url"], "as_of": max(p["as_of"] for p in pts), "role": meta[(source, name)]["role"]}
        counts[f"{source}/{name}"] = (outputs.write_daily if name in DAILY else outputs.write_series)(out, source, name, pts, m)
    gap_cols = ("source", "series_id", "region", "period_start", "period_end", "reason")
    outputs.write(out / "data" / "series" / "gaps.csv", outputs.csv_text(gap_cols, sorted(gaps, key=lambda g: (g["source"], g["series_id"], g["region"], g["period_start"]))))
    # index files
    outputs.write(out / "data" / "index" / "retail.csv", _index_csv(retail, RETAIL_REGIONS))
    outputs.write(out / "data" / "index" / "wholesale.csv", _index_csv(wholesale, ("EU",)))
    rcols = ("index", "month", "region", "local_value", "local_unit", "usd_per_local", "usd_per_kwh", "carried", "provisional")
    outputs.write(out / "data" / "index" / "region_prices.csv", outputs.csv_text(rcols, retail_regions + wholesale_regions))
    outputs.write(out / "data" / "index" / "wholesale_composition.csv",
                  outputs.csv_text(("month", "n_countries", "share_of_eu_inland_demand", "countries"), comp))
    wrows = []
    for y in range(2015, max(int(r["month"][:4]) for r in retail) + 1):
        base = ix.demand_shares(demand, BASKET, y)
        ren = ix.renormalise(base, list(RETAIL_REGIONS))
        for r in BASKET:
            wrows.append({"year": y, "region": r, "demand_twh_year_minus_1": demand[(r, y - 1)], "share_of_four": base[r],
                          "share_retail_renormalised": ren.get(r, "")})
    outputs.write(out / "data" / "index" / "weights.csv", outputs.csv_text(
        ("year", "region", "demand_twh_year_minus_1", "share_of_four", "share_retail_renormalised"), wrows))
    inputs_sha = hashlib.sha256("".join(f"{s}/{n}:{e['sha256']}\n" for (s, n), e in sorted(meta.items())).encode()).hexdigest()
    published = published or snap_date.isoformat()  # default: the date of the raw snapshots; a revision passes its own date
    values = []
    for name, rows in (("retail", retail), ("wholesale", wholesale)):
        for r in rows:
            values.append({"index": name, "month": r["month"], "value_usd_per_kwh": f"{r['level']:.6f}", "index_2015_100": f"{r['index']:.3f}",
                           "status": r["status"], "composition": r["composition"].split("|"), "method_version": HEADLINE_METHOD_VERSION[name]})
    seed = ledger.loads(ledger_seed.read_text()) if ledger_seed and ledger_seed.exists() else []
    lines = ledger.append(seed, values, published, inputs_sha, backfill=not seed)
    outputs.write(out / "ledger" / "index.jsonl", ledger.dumps(seed + lines))
    info = {"method_doc_version": METHOD_DOC_VERSION, "headline_method_version": HEADLINE_METHOD_VERSION, "inputs_sha256": inputs_sha, "published": max(ln["published"] for ln in seed + lines), "snapshots": {f"{s}/{n}": e["sha256"] for (s, n), e in sorted(meta.items())},
            "retail_months": [retail[0]["month"], retail[-1]["month"]], "wholesale_months": [wholesale[0]["month"], wholesale[-1]["month"]],
            "ledger_lines": len(seed) + len(lines), "series_rows": counts}
    outputs.write(out / "data" / "index" / "build_info.json", outputs.json_text(info))
    info["_added"] = len(lines)  # run-specific: returned to callers, never written to build_info.json
    return info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=snapshot.RAW)
    ap.add_argument("--out", type=Path, default=ROOT)
    ap.add_argument("--published", help="date recorded on new ledger lines (default: the raw snapshots' date)")
    ap.add_argument("--ledger-seed", type=Path, default=ROOT / "ledger" / "index.jsonl",
                    help="existing ledger to extend (default: the repo's); pass a non-existent path for a from-scratch backfill")
    args = ap.parse_args(argv)
    info = build(args.raw, args.out, ledger_seed=args.ledger_seed, published=args.published)
    print(json.dumps({k: v for k, v in info.items() if k not in ("snapshots", "series_rows", "_added")}, indent=2))
    print(f"ledger lines added by this run: {info['_added']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
