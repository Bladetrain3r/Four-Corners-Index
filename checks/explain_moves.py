"""Generate checks/explained_moves.md: every month-on-month move above the METHOD.md threshold, decomposed from held data.

    python -m checks.explain_moves [--check]      --check fails if the committed file is not what the data implies

Thresholds (METHOD.md section 8, fixed before any index value existed): Retail 4%, Wholesale 20%. An explanation is a
mechanical attribution, not proof of cause: it separates FX, country composition, and the local price move, then compares
the local move with two drivers we hold (World Bank TTF gas price, Ember EU wind+solar share of generation).
"""
from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal as D
from itertools import pairwise
from pathlib import Path

from pipeline import index as ix
from pipeline import registry

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD = {"retail": 0.04, "wholesale": 0.20}
GAS_MIN_MOVE = 0.10        # TTF must move at least 10% in the same direction to count as gas-aligned
RENEWABLES_MIN_PP = 2.0    # wind+solar share must move at least 2 percentage points against the price
OUT = ROOT / "checks" / "explained_moves.md"


def _csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open()))


def _load(root: Path) -> dict:
    d = root / "data"
    ttf = {r["period_start"][:7]: float(r["value"]) for r in _csv(d / "series" / "worldbank__pink_sheet_monthly.csv")
           if r["series_id"].endswith("natural_gas_europe")}
    gen: dict[str, dict[str, float]] = {}
    for r in _csv(d / "series" / "ember__monthly_generation.csv"):
        if r["region"] == "EU" and r["series_id"] == "ember:monthly:generation":
            gen.setdefault(r["period_start"][:7], {})[r["fuel"]] = float(r["value"])
    price: dict[str, dict[str, D]] = {}
    for r in _csv(d / "series" / "ember__prices_monthly.csv"):
        if r["region"] in registry.EU27:
            price.setdefault(r["period_start"][:7], {})[r["region"]] = ix.dec(r["value"])
    inland = {(r["region"], int(r["period_start"][:4])): ix.dec(r["value"]) for r in _csv(d / "series" / "eurostat__nrg_cb_e.csv")
              if r["series_id"] == "nrg_cb_e:ID:E7000" and r["region"] in registry.EU27}
    return {"index": {n: {r["month"]: r for r in _csv(d / "index" / f"{n}.csv")} for n in ("retail", "wholesale")},
            "region": {(r["index"], r["month"], r["region"]): r for r in _csv(d / "index" / "region_prices.csv")},
            "ttf": ttf, "gen": gen, "price": price, "inland": inland}


def _wind_solar(gen: dict[str, dict[str, float]], m: str) -> float | None:
    g = gen.get(m)
    return (g["wind"] + g["solar"]) / g["total"] if g and "total" in g and "wind" in g and "solar" in g else None


def _mean(price: dict[str, D], inland, month: str, countries: set[str]) -> D:
    y = int(month[:4])
    weights = {c: v for (c, yr), v in inland.items() if yr == y - 1}
    return ix.weighted_mean({c: p for c, p in price.items() if c in countries}, weights)[0]


def wholesale_line(data: dict, a: str, b: str) -> str:
    lv = {m: float(data["index"]["wholesale"][m]["level_usd_per_kwh"]) for m in (a, b)}
    move = lv[b] / lv[a] - 1
    ra, rb = (data["region"][("wholesale", m, "EU")] for m in (a, b))
    local = float(rb["local_value"]) / float(ra["local_value"]) - 1
    fx = float(rb["usd_per_local"]) / float(ra["usd_per_local"]) - 1
    pa, pb = data["price"][a], data["price"][b]
    common = set(pa) & set(pb)
    lfl = float(_mean(pb, data["inland"], b, common) / _mean(pa, data["inland"], a, common)) - 1
    entered = sorted(set(pb) - set(pa))
    left = sorted(set(pa) - set(pb))
    ttf = data["ttf"][b] / data["ttf"][a] - 1
    wsa, wsb = _wind_solar(data["gen"], a), _wind_solar(data["gen"], b)
    dws = None if wsa is None or wsb is None else (wsb - wsa) * 100
    gas = (move > 0) == (ttf > 0) and abs(ttf) >= GAS_MIN_MOVE
    ren = dws is not None and (move > 0) != (dws > 0) and abs(dws) >= RENEWABLES_MIN_PP
    if gas:
        share = abs(ttf) / abs(lfl)
        label = "gas-aligned" if share >= 0.5 else "PARTLY gas-aligned (TTF under half the size of the move)"
        verdict = f"{label}: TTF {ttf:+.1%}, its size is {share:.0%} of the like-for-like price move"
    elif ren:
        verdict = f"renewables-aligned, not gas: wind+solar share {dws:+.1f} pp against a price move of {lfl:+.1%} (TTF {ttf:+.1%})"
    else:
        verdict = f"NOT EXPLAINED by the held drivers (TTF {ttf:+.1%}, wind+solar {dws if dws is None else round(dws, 1)} pp)"
    comp = ""
    if entered or left:
        comp = f"; composition: +{','.join(entered) or '-'} -{','.join(left) or '-'}"
    return (f"- **{b}** wholesale {move:+.1%} ({lv[a]:.6f} to {lv[b]:.6f} USD/kWh): FX {fx:+.1%}, local price {local:+.1%}, "
            f"like-for-like (same countries) {lfl:+.1%}{comp}. {verdict}.")


def render(root: Path = ROOT) -> tuple[str, list[str], float]:
    data = _load(root)
    lines, unexplained = [], []
    rmonths = sorted(data["index"]["retail"])
    moves = [(b, float(data["index"]["retail"][b]["level_usd_per_kwh"]) / float(data["index"]["retail"][a]["level_usd_per_kwh"]) - 1)
             for a, b in pairwise(rmonths)]
    biggest = max(moves, key=lambda x: abs(x[1]))
    over = [(m, v) for m, v in moves if abs(v) > THRESHOLD["retail"]]
    wmonths = sorted(data["index"]["wholesale"])
    body_w = []
    for a, b in pairwise(wmonths):
        move = float(data["index"]["wholesale"][b]["level_usd_per_kwh"]) / float(data["index"]["wholesale"][a]["level_usd_per_kwh"]) - 1
        if abs(move) > THRESHOLD["wholesale"]:
            line = wholesale_line(data, a, b)
            body_w.append(line)
            if "NOT EXPLAINED" in line:
                unexplained.append(b)
    header = (
        "*Generated by `python -m checks.explain_moves` from `data/`; do not edit by hand (`--check` fails if it drifts). "
        "Thresholds from METHOD.md section 8, fixed before any index value existed: Retail 4%, Wholesale 20% month on month. "
        "An explanation here is a mechanical attribution, not proof of cause: it separates FX, country composition and the local price "
        "move, then compares the like-for-like move with two drivers we hold (World Bank TTF; Ember EU wind+solar share). "
        f"A move counts as gas-aligned if TTF moved at least {GAS_MIN_MOVE:.0%} the same way, renewables-aligned if the wind+solar "
        f"share moved at least {RENEWABLES_MIN_PP:.0f} pp against the price and gas is not aligned; otherwise it is listed as NOT EXPLAINED. "
        "Sign-alignment is weak evidence and the size ratio is shown so a reader can judge it. "
        "The classification thresholds were set when this script was written, after a first look at the 32 moves (disclosed).*"
    )
    lines += ["# Explained moves", "", header, "",
              "## Retail index"]
    if over:
        lines += [f"- **{m}** retail {v:+.1%}" for m, v in over]
    else:
        lines.append(f"No month-on-month move above {THRESHOLD['retail']:.0%} in {len(moves)} months; the largest is {biggest[1]:+.2%} ({biggest[0]}). "
                     "The index is smooth because its largest weight is a constant administrative tariff (China) that moves only with CNY/USD, and EU semester "
                     "steps are damped by the other regions (METHOD.md section 11).")
    lines += ["", f"## Wholesale index (EU), {len(body_w)} moves above {THRESHOLD['wholesale']:.0%}", ""] + body_w
    lines += ["", f"Unexplained by the held drivers: {len(unexplained)}" + (f" ({', '.join(unexplained)})" if unexplained else ""), ""]
    return "\n".join(lines), unexplained, biggest[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text, unexplained, _ = render()
    if args.check:
        ok = OUT.exists() and OUT.read_text() == text
        print("explained_moves.md is up to date" if ok else "explained_moves.md is out of date: run python -m checks.explain_moves")
        print(f"{len(unexplained)} moves unexplained by the held drivers")
        return 0 if ok and not unexplained else 1
    OUT.write_text(text)
    print(f"wrote {OUT.name}; {len(unexplained)} unexplained")
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())
