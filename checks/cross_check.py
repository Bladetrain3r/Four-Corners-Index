"""G3 cross-checks: our normalised numbers against figures the publishers themselves state elsewhere.

Tolerances come from checks/tolerances.yaml (committed before this file existed). Every "theirs" figure is parsed from a
saved evidence file or a dated fact in checks/oracles.yaml, never typed here. Usage:
    python -m checks.cross_check [--live]        prints a markdown table, exit 1 if any check fails
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeline import desnz, ecb, eia, ember, eurostat, fetch, registry, worldbank

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
TOL = yaml.safe_load((ROOT / "checks" / "tolerances.yaml").read_text())
ORACLES = yaml.safe_load((ROOT / "checks" / "oracles.yaml").read_text())


@dataclass
class Row:
    check: str
    item: str
    ours: float
    theirs: float
    tolerance: str
    passed: bool
    note: str = ""
    gating: bool = True


def _raw(source: str, name: str) -> tuple[bytes, str]:
    import json
    m = {e["file"]: e for e in json.loads((FIX / source / "MANIFEST.json").read_text())}
    return (FIX / source / name).read_bytes(), m[name]["fetched_at"]


def _pick(points: list[dict[str, Any]], **want: Any) -> list[dict[str, Any]]:
    return [p for p in points if all(p.get(k) == v for k, v in want.items())]


def _one(points: list[dict[str, Any]], **want: Any) -> dict[str, Any]:
    hits = _pick(points, **want)
    if len(hits) != 1:
        raise LookupError(f"expected one point for {want}, found {len(hits)}")
    return hits[0]


def _abs_row(check: str, item: str, ours: float, theirs: float, note: str = "") -> Row:
    tol = TOL["checks"][check]["abs"]
    return Row(check, item, ours, theirs, f"abs {tol}", abs(ours - theirs) <= tol + 1e-12, note)


def _rel_row(check: str, item: str, ours: float, theirs: float, note: str = "") -> Row:
    tol = TOL["checks"][check]["rel"]
    diff = abs(ours - theirs) / abs(theirs) if theirs else float("inf")
    return Row(check, item, ours, theirs, f"rel {tol:.3%}", diff <= tol, f"{note} diff {diff:.3%}".strip())


def _num(pattern: str, text: str) -> float:
    m = re.search(pattern, text)
    if not m:
        raise LookupError(f"oracle sentence not found: {pattern}")
    return float(m.group(1))


# ---------------------------------------------------------------- Eurostat
def eurostat_checks() -> list[Row]:
    text = (FIX / "eurostat" / "statistics_explained_price_sentences.txt").read_text()
    rows = []
    raw, at = _raw("eurostat", "nrg_pc_204_household.json")
    hh = eurostat.parse(raw, "nrg_pc_204", at)
    theirs = {
        "2024-S1": _num(r"peaked in the first half of 2024 at €([0-9.]+)", text),
        "2024-S2": _num(r"edging down to €([0-9.]+) in the second half of 2024", text),
        "2025-S1": _num(r"and €([0-9.]+) in the first half of 2025\.", text),
        "2025-S2": _num(r"ticked up slightly to €([0-9.]+) per kWh", text),
    }
    for label, want in theirs.items():
        start = f"{label[:4]}-01-01" if label.endswith("S1") else f"{label[:4]}-07-01"
        ours = _one(hh, region="EU", series_id="nrg_pc_204:KWH2500-4999:I_TAX:EUR", period_start=start)["value"]
        rows.append(_abs_row("eurostat_household_all_taxes_eu27", label, ours, want))
    excl = {
        "2024-S1": _num(r"€([0-9.]+) per kWh in the first half of 2024 and", text),
        "2024-S2": _num(r"first half of 2024 and €([0-9.]+) per kWh in the second half of 2024", text),
        "2025-S1": _num(r"reaching €([0-9.]+) per kWh in the first half", text),
        "2025-S2": _num(r"per kWh in the first half and €([0-9.]+) per kWh in the second half", text),
    }
    for label, want in excl.items():
        start = f"{label[:4]}-01-01" if label.endswith("S1") else f"{label[:4]}-07-01"
        ours = _one(hh, region="EU", series_id="nrg_pc_204:KWH2500-4999:X_TAX:EUR", period_start=start)["value"]
        rows.append(_abs_row("eurostat_household_excl_taxes_eu27", label, ours, want))
    raw, at = _raw("eurostat", "nrg_pc_205_band_ic.json")
    nh = eurostat.parse(raw, "nrg_pc_205", at)
    nh_theirs = {
        "2024-S1": _num(r"first half of 2024 \(€([0-9.]+) per kWh\)", text),
        "2024-S2": _num(r"second half of 2024, prices excluding taxes showed a marginal increase[^€]*€([0-9.]+)", text),
        "2025-S1": _num(r"first half of 2025 prices excluding taxes decreased to €([0-9.]+)", text),
        "2025-S2": _num(r"further decreased in the second half to €([0-9.]+)", text),
    }
    for label, want in nh_theirs.items():
        start = f"{label[:4]}-01-01" if label.endswith("S1") else f"{label[:4]}-07-01"
        ours = _one(nh, region="EU", series_id="nrg_pc_205:MWH500-1999:X_TAX:EUR", period_start=start)["value"]
        rows.append(_abs_row("eurostat_nonhousehold_excl_taxes_eu27_band_ic", label, ours, want))
    return rows


# ---------------------------------------------------------------- EIA
def eia_checks() -> list[Row]:
    rows = []
    raw, at = _raw("eia", "retail_sales_us_monthly_2025-01_onwards.json")
    ours = eia.parse_retail_price(raw, at)
    lines = (FIX / "eia" / "epm_table_5_6_a_extract.txt").read_text().splitlines()
    us = next(ln for ln in lines if ln.startswith("U.S. Total")).split(" | ")
    cols = {"residential 2026-07": (1, "household", "2026-07-01"), "residential 2025-07": (2, "household", "2025-07-01"),
            "industrial 2026-07": (5, "industrial", "2026-07-01"), "industrial 2025-07": (6, "industrial", "2025-07-01")}
    for label, (i, buyer, start) in cols.items():
        o = _one(ours, region="US", buyer_type=buyer, period_start=start)["value"]
        rows.append(_abs_row("eia_us_retail_price_epm", label, o, float(us[i]) / 100, "EPM cents/kWh / 100"))
    raw, at = _raw("eia", "henry_hub_spot_daily_2026-08.json")
    daily = eia.parse_henry_hub(raw, at, "daily")
    raw, at = _raw("eia", "henry_hub_spot_monthly_2025-10_onwards.json")
    monthly = _one(eia.parse_henry_hub(raw, at, "monthly"), period_start="2026-08-01")["value"]
    mean = statistics.fmean(p["value"] for p in daily)
    rows.append(_abs_row("eia_henry_hub_monthly_vs_daily", f"2026-08 mean of {len(daily)} daily prices", mean, monthly))
    return rows


# ---------------------------------------------------------------- Ember
def ember_checks() -> list[Row]:
    rows = []
    raw, at = _raw("ember", "yearly_generation_global_sample.csv")
    yearly = ember.parse_generation(raw, at, "yearly")
    raw, at = _raw("ember", "monthly_demand_and_total_2025-01_to_2026-08_five_areas.csv")
    monthly = ember.parse_generation(raw, at, "monthly")
    for region in ("EU", "US", "CN", "RU", "ZA"):
        months = [p for p in _pick(monthly, region=region, fuel="demand") if p["period_start"].startswith("2025-")]
        if len(months) != 12:
            rows.append(Row("ember_yearly_demand_vs_sum_of_monthly", region, float("nan"), float("nan"), "12 months", False,
                            f"only {len(months)} monthly Demand rows for 2025", gating=False))
            continue
        y = _one(yearly, region=region, fuel="demand", period_start="2025-01-01")["value"]
        r = _rel_row("ember_yearly_demand_vs_sum_of_monthly", f"{region} 2025", sum(p["value"] for p in months), y)
        r.gating = False  # information row (Ziggy, BLOCKED-G3 item B)
        rows.append(r)
    raw, at = _raw("ember", "price_monthly_2026-06_six_countries.csv")
    pm = ember.parse_prices(raw, at, "monthly")
    raw, at = _raw("ember", "price_daily_2026-06_six_countries.csv")
    daily_gaps: list[dict[str, Any]] = []
    pd_ = ember.parse_prices(raw, at, "daily", gaps=daily_gaps)  # publisher gaps are recorded, not fatal
    t = TOL["checks"]["ember_eu_price_monthly_vs_daily"]
    for region in ("DE", "FR", "IT", "ES", "PL", "NL"):
        m = _one(pm, region=region, period_start="2026-06-01")["value"]
        days = _pick(pd_, region=region)
        mean = statistics.fmean(p["value"] for p in days)
        allow = max(t["rel"] * abs(m), t["abs_floor"])
        n_gaps = len([g for g in daily_gaps if g["region"] == region])
        rows.append(Row("ember_eu_price_monthly_vs_daily", f"{region} 2026-06 ({len(days)} days, {n_gaps} gaps)", mean, m,
                        f"max(rel {t['rel']:.0%}, abs {t['abs_floor']})", abs(mean - m) <= allow, f"diff {mean - m:+.2f} EUR/MWh"))
    # cross-source sanity: Ember US generation vs EIA utility-scale generation
    em = monthly  # the trimmed monthly fixture holds Total generation for every month from 2025-01
    raw, at = _raw("eia", "operational_data_us_generation_monthly_2026-05_onwards.json")
    ei = eia.parse_generation(raw, at)
    lo, hi = TOL["checks"]["ember_us_generation_vs_eia"]["band_rel"]
    for start in ("2026-05-01", "2026-06-01", "2026-07-01"):
        e = _one(em, region="US", fuel="total", series_id="ember:monthly:generation", period_start=start)["value"]
        a = _one(ei, fuel="total", period_start=start)["value"] / 1000.0
        rel = e / a - 1
        rows.append(Row("ember_us_generation_vs_eia", f"US {start[:7]} (ours = Ember)", e, a, f"Ember {lo:.0%}..{hi:.0%} above EIA",
                        lo <= rel <= hi, f"Ember is {rel:+.2%} vs EIA"))
    # Ember EU demand vs Eurostat
    raw, at = _raw("eurostat", "nrg_cb_e_consumption.json")
    es = eurostat.parse(raw, "nrg_cb_e", at)
    ember_eu = _one(yearly, region="EU", fuel="demand", period_start="2025-01-01")["value"]
    inland = _one(es, region="EU", series_id="nrg_cb_e:ID:E7000", period_start="2025-01-01")["value"] / 1000.0
    final = _one(es, region="EU", series_id="nrg_cb_e:FC:E7000", period_start="2025-01-01")["value"] / 1000.0
    rows.append(_rel_row("ember_eu_demand_vs_eurostat_inland_demand", "EU 2025 vs inland demand (ID)", ember_eu, inland))
    rows.append(Row("ember_eu_demand_vs_eurostat_inland_demand", "EU 2025 vs final consumption (FC), information only",
                    ember_eu, final, "info", True, f"diff {abs(ember_eu - final) / final:.1%}: Ember's Demand is not FC"))
    # Russia and China
    so = re.search(r"Потребление электроэнергии в энергосистеме России в 2025 году составило ([0-9 ]+,[0-9]+) млрд",
                   (FIX / "russia" / "so_ups_energy_system_2025_extract.txt").read_text())
    if not so:
        raise LookupError("SO UPS consumption sentence not found")
    so_twh = float(so.group(1).replace(" ", "").replace(",", "."))
    ru = _one(yearly, region="RU", fuel="demand", period_start="2025-01-01")
    rows.append(_rel_row("ember_russia_demand_vs_so_ups", "RU 2025 (low_confidence tier)", ru["value"], so_twh))
    cn = _one(monthly, region="CN", fuel="demand", period_start="2026-08-01")["value"]
    rows.append(_rel_row("ember_china_demand_vs_nea", "CN 2026-08", cn, ORACLES["nea_china_consumption_2026_08"]["value_twh"]))
    return rows


# ---------------------------------------------------------------- ECB and World Bank
def fx_and_commodity_checks() -> list[Row]:
    rows = []
    raw, at = _raw("ecb", "exr_monthly_usd_cny_zar_2022-01.csv")
    monthly = ecb.parse(raw, at)
    raw, at = _raw("ecb", "exr_daily_usd_cny_zar_2026-06-01.csv")
    daily = ecb.parse(raw, at)
    for cur in ("USD", "CNY", "ZAR"):
        for month in ("2026-06", "2026-07", "2026-08"):
            days = [p["value"] for p in daily if p["region"] == cur and p["period_start"].startswith(month)]
            m = _one(monthly, region=cur, period_start=f"{month}-01")["value"]
            rows.append(_rel_row("ecb_monthly_vs_daily_mean", f"{cur} {month} ({len(days)} days)", statistics.fmean(days), m))
    raw, at = _raw("worldbank", "pink_sheet_monthly_gas_coal_last36.csv")
    wb = {p["period_start"]: p["value"] for p in worldbank.parse_csv_extract(raw, at)
          if p["series_id"] == "worldbank:pink_sheet:natural_gas_europe"}
    imf_raw, _ = _raw("worldbank", "imf_pcps_ttf_coal_last36_monthly.csv")
    imf = {}
    for r in csv.DictReader(io.StringIO(imf_raw.decode("utf-8-sig"))):
        if r["INDICATOR"] == "PNGASEU":
            y, m = r["TIME_PERIOD"].split("-M")
            imf[f"{y}-{m}-01"] = float(r["OBS_VALUE"])
    months = sorted(set(wb) & set(imf))
    t = TOL["checks"]["worldbank_vs_imf_europe_gas"]
    tol, window = t["rel"], t["gating_window_months"]

    def rel(k: str) -> float:
        return abs(wb[k] - imf[k]) / imf[k]

    recent = months[-window:]
    worst_recent = max(recent, key=rel)
    rows.append(Row("worldbank_vs_imf_europe_gas", f"latest {len(recent)} months, worst {worst_recent[:7]}", wb[worst_recent],
                    imf[worst_recent], f"rel {tol:.0%} each of {window} months", len(recent) == window and all(rel(k) <= tol for k in recent),
                    f"worst diff {rel(worst_recent):.2%}"))
    outside = [k for k in months if rel(k) > tol]
    worst = max(months, key=rel)
    rows.append(Row("worldbank_vs_imf_europe_gas", f"all {len(months)} months (information), worst {worst[:7]}", wb[worst], imf[worst],
                    f"rel {tol:.0%}", not outside,
                    f"{len(outside)} months outside: {', '.join(k[:7] for k in outside) or 'none'}; median diff "
                    f"{statistics.median(rel(k) for k in months):.2%}", gating=False))
    return rows


# ---------------------------------------------------------------- United Kingdom
def uk_checks() -> list[Row]:
    """DESNZ (UK column) against Eurostat's own UK series in national currency, over the semesters both hold."""
    rows = []
    jobs = (
        ("desnz_household_vs_eurostat_uk", "table_562_medium_domestic_eu_uk.csv", "5.6.2", "nrg_pc_204_uk_dc_nac.json", "nrg_pc_204",
         "nrg_pc_204:KWH2500-4999", {"incl_tax": "I_TAX", "excl_tax": "X_TAX"}),
        ("desnz_nonhousehold_vs_eurostat_uk", "table_542_medium_nondomestic_eu_uk.csv", "5.4.2", "nrg_pc_205_uk_id_nac.json", "nrg_pc_205",
         "nrg_pc_205:MWH2000-19999", {"incl_tax": "X_VAT", "excl_tax": "X_TAX"}),
    )
    for check, d_file, table, e_file, dataset, prefix, mapping in jobs:
        raw, at = _raw("desnz", d_file)
        ours = desnz.parse(raw, at, table, "fixture")
        raw, at = _raw("eurostat", e_file)
        theirs = eurostat.parse(raw, dataset, at)
        for level, tax in mapping.items():
            sid_d = f"desnz:qep_{table}:medium:{level}"
            sid_e = f"{prefix}:{tax}:NAC"
            eu = {p["period_start"]: p["value"] for p in theirs if p["series_id"] == sid_e}
            for start in sorted(eu):
                o = _one(ours, series_id=sid_d, period_start=start)["value"]
                rows.append(_abs_row(check, f"{level} vs {tax} {start[:4]}-S{1 if start[5:7] == '01' else 2}", o, eu[start]))
    return rows


# ---------------------------------------------------------------- sanity ranges
def sanity_checks(points: list[dict[str, Any]]) -> list[Row]:
    rows = []
    for name, r in TOL["sanity_ranges"].items():
        sel = [p for p in points if p["series_id"].startswith(r["series_prefix"])
               and (("series_contains" not in r) or r["series_contains"] in p["series_id"])
               and (("series_contains_any" not in r) or any(c in p["series_id"] for c in r["series_contains_any"]))
               and (("unit" not in r) or p["unit"] == r["unit"]) and (("region" not in r) or p["region"] == r["region"])]
        if not sel:
            rows.append(Row("sanity", name, float("nan"), float("nan"), f"{r['min']}..{r['max']}", False, "no points matched"))
            continue
        lo, hi = min(p["value"] for p in sel), max(p["value"] for p in sel)
        rows.append(Row("sanity", name, lo, hi, f"{r['min']}..{r['max']}", r["min"] <= lo and hi <= r["max"], f"{len(sel)} points, min..max shown"))
    return rows


def fixture_points() -> list[dict[str, Any]]:
    out = []
    for req in registry.REQUESTS:
        out += fetch.parse(fetch.load(req, "fixture"), gaps=[])
    return out


def live_points() -> list[dict[str, Any]]:
    out = []
    for req in registry.REQUESTS:
        out += fetch.parse(fetch.load(req, "live"), gaps=[])
    return out


def run(live: bool = False) -> list[Row]:
    rows = eurostat_checks() + eia_checks() + ember_checks() + fx_and_commodity_checks() + uk_checks()
    return rows + sanity_checks(live_points() if live else fixture_points())


def markdown(rows: list[Row]) -> str:
    out = ["| check | item | ours | theirs | tolerance | pass | note |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        status = ("PASS" if r.passed else "FAIL") if r.gating else ("INFO ok" if r.passed else "INFO outside")
        out.append(f"| {r.check} | {r.item} | {r.ours:.6g} | {r.theirs:.6g} | {r.tolerance} | {status} | {r.note} |")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="apply the sanity ranges to live-fetched data too")
    args = ap.parse_args(argv)
    rows = run(args.live)
    print(markdown(rows))
    gating = [r for r in rows if r.gating]
    failed = [r for r in gating if not r.passed]
    print(f"\n{len(gating) - len(failed)} of {len(gating)} gating rows passed; {len(rows) - len(gating)} information rows")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
