"""Index maths (METHOD.md v1). Pure functions on Decimal values; no I/O, no network, no clock.

Months are 'YYYY-MM' strings. Every published number goes through `q6` (USD/kWh) or `q3` (index points) exactly once.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

Q6 = Decimal("0.000001")
Q3 = Decimal("0.001")
W = Decimal("0.000000000001")  # weights to 12 decimals


def q6(x: Decimal) -> Decimal:
    return x.quantize(Q6, rounding=ROUND_HALF_EVEN)


def q3(x: Decimal) -> Decimal:
    return x.quantize(Q3, rounding=ROUND_HALF_EVEN)


def dec(x: float | str) -> Decimal:
    return Decimal(str(x))


def next_month(m: str) -> str:
    y, mo = int(m[:4]), int(m[5:])
    return f"{y + 1}-01" if mo == 12 else f"{y}-{mo + 1:02d}"


def months(start: str, end: str) -> list[str]:
    out, m = [], start
    while m <= end:
        out.append(m)
        m = next_month(m)
    return out


def month_end(m: str) -> date:
    y, mo = int(m[:4]), int(m[5:])
    nxt = date(y + 1, 1, 1) if mo == 12 else date(y, mo + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def expand_period(start: str, end: str, value: Decimal, into: dict[str, Decimal]) -> None:
    """A value published for a period applies to every month inside it (start, end are ISO dates)."""
    for m in months(start[:7], end[:7]):
        into[m] = value


@dataclass(frozen=True)
class RegionMonth:
    region: str
    month: str
    local_value: Decimal
    local_unit: str
    usd_per_local: Decimal  # USD per one unit of local currency, 1 for USD
    usd: Decimal  # USD per kWh, q6
    carried: bool  # value carried forward from an earlier period
    provisional: bool
    note: str = ""


def carry_forward(observed: dict[str, Decimal], month_list: list[str], limit: int | None) -> dict[str, tuple[Decimal, bool]]:
    """Value for each month: the observed one, else the last observed one carried (at most `limit` months; None = unlimited)."""
    out: dict[str, tuple[Decimal, bool]] = {}
    earlier = [k for k in observed if month_list and k < month_list[0]]
    last_m: str | None = max(earlier) if earlier else None  # an observation before the list can still be carried into it
    for m in month_list:
        if m in observed:
            out[m] = (observed[m], False)
            last_m = m
        elif last_m is not None:
            gap = len(months(last_m, m)) - 1
            if limit is None or gap <= limit:
                out[m] = (observed[last_m], True)
    return out


def demand_shares(demand: dict[tuple[str, int], Decimal], regions: tuple[str, ...], year: int) -> dict[str, Decimal]:
    """w(r, y): share of the demand of year y-1 among the basket regions (all of them, priced or not)."""
    src = year - 1
    missing = [r for r in regions if (r, src) not in demand]
    if missing:
        raise KeyError(f"no demand for {missing} in {src}")
    total = sum(demand[(r, src)] for r in regions)
    return {r: (demand[(r, src)] / total).quantize(W, rounding=ROUND_HALF_EVEN) for r in regions}


def renormalise(weights: dict[str, Decimal], included: list[str]) -> dict[str, Decimal]:
    total = sum(weights[r] for r in included)
    return {r: (weights[r] / total).quantize(W, rounding=ROUND_HALF_EVEN) for r in included}


@dataclass(frozen=True)
class Combined:
    month: str
    level: Decimal  # q6, USD/kWh
    contributions: dict[str, Decimal]  # q6 each, sum equals level up to rounding
    weights: dict[str, Decimal]  # renormalised
    composition: tuple[str, ...]


def combine(month: str, usd: dict[str, Decimal], base_weights: dict[str, Decimal], equal: bool = False) -> Combined:
    included = sorted(usd)
    w = {r: Decimal(1) / len(included) for r in included} if equal else renormalise(base_weights, included)
    if equal:
        w = {r: v.quantize(W, rounding=ROUND_HALF_EVEN) for r, v in w.items()}
    contrib = {r: q6(w[r] * usd[r]) for r in included}
    with localcontext() as ctx:
        ctx.prec = 40
        level = q6(sum((w[r] * usd[r] for r in included), Decimal(0)))
    return Combined(month, level, contrib, w, tuple(included))


def index_form(levels: dict[str, Decimal], base_year: str = "2015") -> dict[str, Decimal]:
    """100 x level / mean of the base year's twelve published monthly levels."""
    base = [levels[m] for m in months(f"{base_year}-01", f"{base_year}-12") if m in levels]
    if len(base) != 12:
        raise ValueError(f"base year {base_year} needs 12 months, has {len(base)}")
    mean = sum(base, Decimal(0)) / 12
    return {m: q3(Decimal(100) * v / mean) for m, v in levels.items()}


def weighted_mean(values: dict[str, Decimal], weights: dict[str, Decimal]) -> tuple[Decimal, dict[str, Decimal]]:
    """Mean of `values` (by country) weighted by `weights`, renormalised over the countries present in `values`."""
    present = sorted(k for k in values if k in weights)
    if not present:
        raise ValueError("no country has both a value and a weight")
    w = renormalise({k: weights[k] for k in present}, present)
    with localcontext() as ctx:
        ctx.prec = 40
        return sum((w[k] * values[k] for k in present), Decimal(0)), w
