"""Builds the JSON documents the static site reads, from the CSV outputs in data/ and the hand-authored facts in data/manual/.

Pure functions of files: same inputs, same output. Nothing here talks to the network.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pipeline import ledger

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FUELS = ("coal", "gas", "oil_other_fossil", "nuclear", "hydro", "wind", "solar", "bio_other")
FUEL_LABEL = {"coal": "Coal", "gas": "Gas", "oil_other_fossil": "Oil and other fossil", "nuclear": "Nuclear", "hydro": "Hydro",
              "wind": "Wind", "solar": "Solar", "bio_other": "Bioenergy and other renewables"}
_FUEL_MAP = {"coal": "coal", "gas": "gas", "other_fossil": "oil_other_fossil", "nuclear": "nuclear", "hydro": "hydro", "wind": "wind",
             "solar": "solar", "bioenergy": "bio_other", "other_renewables": "bio_other"}
CURRENCIES = ("USD", "CNY", "ZAR", "GBP")


def rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def num(x: str) -> float | None:
    return float(x) if x not in ("", None) else None


def meta(name: str) -> dict[str, Any]:
    return json.loads((DATA / "series" / f"{name}.meta.json").read_text())


def series_rows(name: str) -> list[dict[str, str]]:
    return rows(DATA / "series" / f"{name}.csv")


def manual(name: str) -> Any:
    return json.loads((DATA / "manual" / name).read_text())


def fx_table() -> dict[str, dict[str, float]]:
    """month -> currency units per EUR (ECB monthly averages), for USD, CNY, ZAR, GBP."""
    out: dict[str, dict[str, float]] = {}
    for r in series_rows("ecb__exr_monthly"):
        if r["series_id"].startswith("ecb:EXR:M:") and r["region"] in CURRENCIES:
            out.setdefault(r["period_start"][:7], {})[r["region"]] = float(r["value"])
    return out


def _index_rows(name: str, regions: tuple[str, ...]) -> list[dict[str, Any]]:
    out = []
    for r in rows(DATA / "index" / f"{name}.csv"):
        row: dict[str, Any] = {"m": r["month"], "status": r["status"], "level": float(r["level_usd_per_kwh"]), "index": float(r["index_2015_100"]),
                               "equal_level": float(r["equal_level_usd_per_kwh"]), "equal_index": float(r["equal_index_2015_100"]),
                               "composition": r["composition"].split("|"),
                               "contrib": {g: float(r[f"contrib_{g}"]) for g in regions if r.get(f"contrib_{g}")},
                               "weights": {g: float(r[f"weight_{g}"]) for g in regions if r.get(f"weight_{g}")}}
        if "exchina_level_usd_per_kwh" in r:
            row["ex_level"], row["ex_index"] = float(r["exchina_level_usd_per_kwh"]), float(r["exchina_index_2015_100"])
            row["ex_contrib"] = {g: float(r[f"exchina_contrib_{g}"]) for g in ("EU", "US", "GB")}
        out.append(row)
    return out


def index_doc() -> dict[str, Any]:
    lines = ledger.loads((ROOT / "ledger" / "index.jsonl").read_text())
    latest = ledger.latest(lines)
    by_hash = {ln["hash"]: ln for ln in lines}
    retail = _index_rows("retail", ("EU", "US", "CN", "GB"))
    wholesale = _index_rows("wholesale", ("EU",))
    for name, rws in (("retail", retail), ("wholesale", wholesale)):
        for r in rws:
            e = latest[(name, r["m"])]
            r["published"], r["method_version"] = e["published"], e["method_version"]
    revisions = [{"index": ln["index"], "month": ln["month"], "from": by_hash[ln["supersedes"]]["value_usd_per_kwh"], "to": ln["value_usd_per_kwh"],
                  "from_status": by_hash[ln["supersedes"]]["status"], "to_status": ln["status"], "published": ln["published"],
                  "method_version": ln["method_version"], "hash": ln["hash"][:16]} for ln in lines if "supersedes" in ln]
    comp = {r["month"]: {"n": int(r["n_countries"]), "share": float(r["share_of_eu_inland_demand"]), "countries": r["countries"].split("|")}
            for r in rows(DATA / "index" / "wholesale_composition.csv")}
    weights = [{"year": int(r["year"]), "region": r["region"], "demand_twh": float(r["demand_twh_year_minus_1"]), "share_of_five": float(r["share_of_four"]),
                "share_retail": num(r["share_retail_renormalised"])} for r in rows(DATA / "index" / "weights.csv")]
    return {"retail": retail, "wholesale": wholesale, "wholesale_composition": comp, "weights": weights, "revisions": revisions,
            "ledger": {"lines": len(lines), "head": lines[-1]["hash"], "tail": lines[-12:]},
            "fx": {m: {c: v for c, v in d.items()} for m, d in fx_table().items()},
            "quality": {"retail": {"EU": "A", "US": "A", "CN": "C", "GB": "A"}, "wholesale": {"EU": "A"}}}


def _latest(pts: list[dict[str, str]]) -> dict[str, str]:
    return max(pts, key=lambda r: r["period_start"])


def _card_from(pts: list[dict[str, str]], fact: dict[str, Any], m: dict[str, Any], per_kwh_divisor: float = 1.0, provisional: bool = False,
               note: str = "") -> dict[str, Any]:
    p = _latest(pts)
    return {"status": "value", "value": float(p["value"]) / per_kwh_divisor, "currency": p["currency"] or "USD", "period_start": p["period_start"],
            "period_end": p["period_end"], "as_of": m["as_of"], "retrieved": m["retrieved_at"][:10], "source": fact["source"], "url": fact.get("url", ""),
            "source_id": fact.get("source_id", ""), "confidence": fact.get("confidence", p.get("confidence", "primary")), "provisional": provisional, "note": note}


def _mix(region: str, months_by: dict[str, dict[str, dict[str, float]]], ci: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    out = []
    for m in sorted(months_by):
        d = months_by[m].get(region)
        if not d or "total" not in d or d["total"] <= 0:
            continue
        shares = {k: 0.0 for k in FUELS}
        for src, dst in _FUEL_MAP.items():
            if src in d:
                shares[dst] += d[src] / d["total"]
        out.append({"m": m, "shares": {k: round(v, 4) for k, v in shares.items()}, "total_twh": round(d["total"], 3), "demand_twh": round(d.get("demand", 0.0), 3),
                    "carbon": round(ci.get(m, {}).get(region, 0.0), 1) if ci.get(m, {}).get(region) is not None else None})
    return out


def regions_docs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    facts = manual("regions.json")
    fx = fx_table()
    last_fx_month = max(fx)
    gen: dict[str, dict[str, dict[str, float]]] = {}
    ci: dict[str, dict[str, float]] = {}
    for r in series_rows("ember__monthly_generation"):
        m = r["period_start"][:7]
        if r["series_id"] == "ember:monthly:generation":
            gen.setdefault(m, {}).setdefault(r["region"], {})[r["fuel"]] = float(r["value"])
        elif r["series_id"] == "ember:monthly:emissions_intensity":
            ci.setdefault(m, {})[r["region"]] = float(r["value"])
    ember_m = meta("ember__monthly_generation")
    region_price = {(r["index"], r["month"], r["region"]): r for r in rows(DATA / "index" / "region_prices.csv")}
    retail_months = sorted({m for (i, m, _r) in region_price if i == "retail"})
    wholesale_months = sorted({m for (i, m, _r) in region_price if i == "wholesale"})
    cards_src = {
        "EU": {"household": ("eurostat__nrg_pc_204", lambda r: r["region"] == "EU" and r["series_id"] == "nrg_pc_204:KWH2500-4999:I_TAX:EUR"),
               "industrial": ("eurostat__nrg_pc_205", lambda r: r["region"] == "EU" and r["series_id"] == "nrg_pc_205:MWH2000-19999:X_VAT:EUR")},
        "US": {"household": ("eia__retail_price", lambda r: r["region"] == "US" and r["buyer_type"] == "household"),
               "industrial": ("eia__retail_price", lambda r: r["region"] == "US" and r["buyer_type"] == "industrial")},
        "GB": {"household": ("desnz__qep_562", lambda r: r["series_id"] == "desnz:qep_5.6.2:medium:incl_tax"),
               "industrial": ("desnz__qep_542", lambda r: r["series_id"] == "desnz:qep_5.4.2:medium:incl_tax")}}
    summary, detail = [], {}
    for reg in facts["regions"]:
        rid = reg["id"]
        cards: dict[str, Any] = {}
        for kind in ("household", "industrial", "wholesale"):
            fact = reg["cards"][kind]
            if "gap" in fact:
                cards[kind] = {"status": "gap", "reason": fact["gap"]}
                continue
            if kind == "wholesale":  # EU only
                row = region_price[("wholesale", wholesale_months[-1], "EU")]
                m = meta("ember__prices_monthly")
                cards[kind] = {"status": "value", "value": float(row["local_value"]) / 1000.0, "currency": "EUR", "period_start": wholesale_months[-1] + "-01",
                               "period_end": wholesale_months[-1] + "-28", "as_of": m["as_of"], "retrieved": m["retrieved_at"][:10], "source": fact["source"],
                               "url": fact["url"], "source_id": fact["source_id"], "confidence": "primary", "provisional": False, "note": ""}
            elif rid == "ZA":  # two hand-entered Eskom figures; never fetched
                e = manual("eskom_tariffs.json")
                f = e["facts"][kind]
                cards[kind] = {"status": "value", "value": f["value"], "currency": f["currency"], "period_start": f["period_start"], "period_end": f["period_end"],
                               "period_label": f["period_label"], "as_of": e["read"], "retrieved": e["read"], "source": fact["source"], "url": fact["url"], "source_id": "eskom",
                               "confidence": f["confidence"], "provisional": False, "note": f["note"]}
            elif rid == "CN":
                t = next(s for s in manual("china_household_tariff.json")["series"] if s["in_index"])
                cards[kind] = {"status": "value", "value": t["value"], "currency": "CNY", "period_start": t["valid_from"], "period_end": t["last_confirmed"],
                               "as_of": t["last_confirmed"], "retrieved": t["last_confirmed"], "source": fact["source"], "url": fact["url"], "source_id": "shanghai",
                               "confidence": "low_confidence", "provisional": False, "note": "An administrative tariff; the period shown is 'in force from ... last confirmed'."}
            else:
                name, pred = cards_src[rid][kind]
                pts = [r for r in series_rows(name) if pred(r)]
                m = meta(name)
                prov = rid == "US"
                note = "Preliminary: EIA revises recent months." if prov else ""
                cards[kind] = _card_from(pts, fact, m, provisional=prov, note=note)
        mix = _mix(rid, gen, ci)
        latest_mix = mix[-1] if mix else None
        entry = {"id": rid, "name": reg["name"], "short": reg["short"], "in_basket": reg["in_basket"], "badge": reg["badge"], "badge_note": reg["badge_note"],
                 "cards": cards, "mix": None}
        if latest_mix:
            entry["mix"] = dict(latest_mix, as_of=ember_m["as_of"], retrieved=ember_m["retrieved_at"][:10], source=facts["mix_source"]["source"],
                                url=facts["mix_source"]["url"], confidence="low_confidence" if rid == "RU" else "primary",
                                fuels=[{"id": f, "label": FUEL_LABEL[f]} for f in FUELS])
        summary.append(entry)
        detail[rid] = _region_detail(rid, entry, region_price, retail_months, wholesale_months, mix)
    return {"regions": summary, "fx_latest": {"month": last_fx_month, "per_eur": {"EUR": 1.0, **fx[last_fx_month]}}}, detail


def _period_series(name: str, pred) -> list[dict[str, Any]]:
    return [{"s": r["period_start"], "e": r["period_end"], "v": float(r["value"])} for r in sorted(series_rows(name), key=lambda r: r["period_start"]) if pred(r)]


def _region_detail(rid: str, entry: dict[str, Any], region_price, retail_months, wholesale_months, mix) -> dict[str, Any]:
    d: dict[str, Any] = {"id": rid, "name": entry["name"], "badge": entry["badge"], "mix_over_time": mix, "series": {}, "sources": [], "gaps": {
        k: c["reason"] for k, c in entry["cards"].items() if c["status"] == "gap"}}
    s = d["series"]
    if rid == "EU":
        s["household"] = {"label": "Household (band DC, all taxes)", "currency": "EUR", "points": _period_series("eurostat__nrg_pc_204", lambda r: r["region"] == "EU" and r["series_id"].endswith(":KWH2500-4999:I_TAX:EUR")), "unit": "EUR/kWh"}
        s["industrial"] = {"label": "Industrial (band ID, excl. VAT and recoverable levies)", "currency": "EUR", "unit": "EUR/kWh", "points": _period_series("eurostat__nrg_pc_205", lambda r: r["region"] == "EU" and r["series_id"] == "nrg_pc_205:MWH2000-19999:X_VAT:EUR")}
        s["industrial_comparison"] = {"label": "Comparison: band IC (500-1,999 MWh/yr), Eurostat's own headline band", "currency": "EUR", "unit": "EUR/kWh", "points": _period_series("eurostat__nrg_pc_205_ic", lambda r: r["region"] == "EU" and r["series_id"] == "nrg_pc_205:MWH500-1999:X_VAT:EUR")}
        s["wholesale"] = {"label": "Wholesale (day-ahead, EU-27 demand-weighted)", "currency": "EUR", "unit": "EUR/kWh", "points": [{"s": m + "-01", "e": m + "-28", "v": float(region_price[("wholesale", m, "EU")]["local_value"]) / 1000.0} for m in wholesale_months]}
        comp: dict[str, dict[str, float]] = {}
        for r in series_rows("eurostat__nrg_pc_204_c"):
            if r["region"] == "EU" and r["component"] in ("NRG_SUP", "NETC", "TAX_FEE_LEV_CHRG", "VAT"):
                comp.setdefault(r["period_start"][:4], {})[r["component"]] = float(r["value"])
        hh = d["series"]["household"]["points"]
        years = [{"year": y, "energy_supply": v["NRG_SUP"], "network": v["NETC"], "other_taxes_levies": v["TAX_FEE_LEV_CHRG"] - v["VAT"], "vat": v["VAT"]}
                 for y, v in sorted(comp.items()) if len(v) == 4]
        recon = []
        for c in years:
            sem = [p["v"] for p in hh if p["s"].startswith(c["year"])]
            total = c["energy_supply"] + c["network"] + c["other_taxes_levies"] + c["vat"]
            if len(sem) == 2:
                recon.append({"year": c["year"], "components_total": total, "half_year_mean": sum(sem) / 2, "difference": total - sum(sem) / 2})
        d["components"] = {"unit": "EUR/kWh", "years": years, "reconciliation": recon,
                           "note": ("Annual, as Eurostat publishes it. 'Other taxes and levies' excludes VAT (the published taxes item includes it, so it is not added twice). "
                                    "The components do not always add up to the mean of the two half-year prices: the difference is shown in the reconciliation and is not explained by these data.")}
        d["sources"] = ["eurostat", "ember", "ecb"]
    elif rid == "US":
        s["household"] = {"label": "Residential (all customers)", "currency": "USD", "unit": "USD/kWh", "points": _period_series("eia__retail_price", lambda r: r["region"] == "US" and r["buyer_type"] == "household")}
        s["industrial"] = {"label": "Industrial (all customers)", "currency": "USD", "unit": "USD/kWh", "points": _period_series("eia__retail_price", lambda r: r["region"] == "US" and r["buyer_type"] == "industrial")}
        d["sources"] = ["eia", "ember"]
    elif rid == "GB":
        s["household"] = {"label": "Household (band DC-equivalent, incl. all taxes)", "currency": "GBP", "unit": "GBP/kWh", "points": _period_series("desnz__qep_562", lambda r: r["series_id"] == "desnz:qep_5.6.2:medium:incl_tax")}
        s["industrial"] = {"label": "Industrial (band ID-equivalent, excl. VAT)", "currency": "GBP", "unit": "GBP/kWh", "points": _period_series("desnz__qep_542", lambda r: r["series_id"] == "desnz:qep_5.4.2:medium:incl_tax")}
        d["sources"] = ["desnz", "ember", "ecb"]
    elif rid == "CN":
        t = [x for x in manual("china_household_tariff.json")["series"]]
        s["household"] = {"label": "Household: Shanghai first tier (administrative tariff)", "currency": "CNY", "unit": "CNY/kWh",
                          "points": [{"s": m + "-01", "e": m + "-28", "v": t[0]["value"]} for m in retail_months]}
        s["household_comparison"] = {"label": "Comparison: Guangdong (Shantou price list) first tier, from 2021-12", "currency": "CNY", "unit": "CNY/kWh",
                                     "points": [{"s": m + "-01", "e": m + "-28", "v": t[1]["value"]} for m in retail_months if m >= "2021-12"]}
        d["sources"] = ["shanghai", "ember", "ecb"]
    elif rid == "ZA":
        d["sources"] = ["eskom", "ember"]
    else:
        d["sources"] = ["ember"]
    if rid in ("EU", "US", "CN", "GB"):
        d["household_usd_monthly"] = [{"m": m, "v": float(region_price[("retail", m, rid)]["usd_per_kwh"]), "carried": region_price[("retail", m, rid)]["carried"] == "1"} for m in retail_months]
    return d


def drivers_doc() -> dict[str, Any]:
    notes = manual("regions.json")["drivers_notes"]
    fx = fx_table()
    fm = sorted(fx)[-13:]

    def tail(pts: list[tuple[str, float]]) -> list[dict[str, Any]]:
        return [{"m": m, "v": v} for m, v in pts[-13:]]

    def monthly(name: str, series_tail: str, region: str) -> list[tuple[str, float]]:
        return sorted((r["period_start"][:7], float(r["value"])) for r in series_rows(name) if r["series_id"].endswith(series_tail) and r["region"] == region)

    wb, wbm = "worldbank__pink_sheet_monthly", meta("worldbank__pink_sheet_monthly")
    defs = [("ttf", "Natural gas, Europe (TTF)", "USD/MMBtu", monthly(wb, "natural_gas_europe", "EU"), wbm, "The World Bank Pink Sheet", "worldbank"),
            ("henry_hub", "Natural gas, US (Henry Hub spot)", "USD/MMBtu", sorted((r["period_start"][:7], float(r["value"])) for r in series_rows("eia__henry_hub_monthly")), meta("eia__henry_hub_monthly"), "EIA", "eia"),
            ("coal_au", "Coal, Australia (Newcastle)", "USD/t", monthly(wb, "coal_australia", "AU"), wbm, "The World Bank Pink Sheet", "worldbank"),
            ("coal_za", "Coal, South Africa (Richards Bay)", "USD/t", monthly(wb, "coal_south_africa", "ZA"), wbm, "The World Bank Pink Sheet", "worldbank"),
            ("eurusd", "USD per EUR", "USD per EUR", [(m, fx[m]["USD"]) for m in sorted(fx)], meta("ecb__exr_monthly"), "European Central Bank", "ecb"),
            ("cnyusd", "CNY per USD", "CNY per USD", [(m, fx[m]["CNY"] / fx[m]["USD"]) for m in sorted(fx)], meta("ecb__exr_monthly"), "European Central Bank (cross rate, modified)", "ecb"),
            ("zarusd", "ZAR per USD", "ZAR per USD", [(m, fx[m]["ZAR"] / fx[m]["USD"]) for m in sorted(fx)], meta("ecb__exr_monthly"), "European Central Bank (cross rate, modified)", "ecb"),
            ("gbpusd", "GBP per USD", "GBP per USD", [(m, fx[m]["GBP"] / fx[m]["USD"]) for m in sorted(fx)], meta("ecb__exr_monthly"), "European Central Bank (cross rate, modified)", "ecb")]
    items = []
    for did, label, unit, pts, m, src, sid in defs:
        s = tail(pts)
        prev = next((v for mm, v in pts if mm == _shift(s[-1]["m"], -12)), None)
        items.append({"status": "value", "id": did, "label": label, "unit": unit, "series": s, "latest": s[-1], "change_12m": (s[-1]["v"] / prev - 1) if prev else None,
                      "as_of": m["as_of"], "retrieved": m["retrieved_at"][:10], "source": src, "source_id": sid, "badge": "A"})
    items.append({"status": "gap", "id": "carbon", "label": "EU carbon price (EUA)", "reason": notes["carbon"]})
    items.append({"status": "gap", "id": "rub", "label": "RUB per USD", "reason": notes["rub"]})
    del fm
    return {"items": items}


def _shift(m: str, months: int) -> str:
    y, mo = int(m[:4]), int(m[5:])
    t = y * 12 + (mo - 1) + months
    return f"{t // 12}-{t % 12 + 1:02d}"
