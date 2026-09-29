"""STOP-2 chart from data/index/*.csv (matplotlib, a dev dependency; not part of the pipeline).

Design (dataviz skill): one axis per panel, no dual axes; validated categorical slots 1-3 (blue, orange, aqua; aqua has a contrast
WARN so every series is direct-labelled and the data is in the CSV table); text in ink tokens, never the series colour;
provisional months shaded and labelled.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2dc"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def load(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader((ROOT / "data" / "index" / f"{name}.csv").open()))


def d(m: str) -> date:
    return date(int(m[:4]), int(m[5:]), 1)


def style(ax, title: str, ylabel: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel, color=INK2, fontsize=10)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def shade_provisional(ax, rows, label: bool = True) -> None:
    prov = [d(r["month"]) for r in rows if r["status"] == "provisional"]
    if prov:
        ax.axvspan(prov[0], prov[-1], color="#f0efe9", zorder=0)
    if prov and label:
        ax.text(prov[0], ax.get_ylim()[1], " provisional", va="top", ha="left", fontsize=8.5, color=INK2)


def main() -> None:
    retail, wholesale = load("retail"), load("wholesale")
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 12), facecolor=SURFACE)
    xs = [d(r["month"]) for r in retail]

    ax = axes[0]
    style(ax, "Retail index: weighted (headline), equal-weighted, and excluding China (USD per kWh, nominal)", "USD/kWh")
    w = [float(r["level_usd_per_kwh"]) for r in retail]
    e = [float(r["equal_level_usd_per_kwh"]) for r in retail]
    ax.plot(xs, w, color=BLUE, linewidth=2, label="Weighted (headline)")
    ax.plot(xs, e, color=ORANGE, linewidth=2, label="Equal-weighted")
    x_ = [float(r["exchina_level_usd_per_kwh"]) for r in retail]
    ax.plot(xs, x_, color=INK2, linewidth=2, linestyle=(0, (5, 3)), label="Excluding China (EU + US)")
    ax.set_ylim(0.10, 0.27)
    shade_provisional(ax, retail)
    ax.text(xs[-1], w[-1] - 0.006, f"weighted {w[-1]:.3f}", color=INK, fontsize=9, ha="right", va="top")
    ax.text(xs[-1], e[-1] - 0.007, f"equal {e[-1]:.3f}", color=INK, fontsize=9, ha="right", va="top")
    ax.text(xs[-1], x_[-1] + 0.005, f"ex-China {x_[-1]:.3f}", color=INK, fontsize=9, ha="right", va="bottom")
    ax.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=INK2, ncol=3)

    ax = axes[1]
    style(ax, "Retail index: contribution by region (weight x price, USD per kWh; they sum to the headline)", "USD/kWh")
    series = [("EU", BLUE, "EU"), ("US", ORANGE, "US"), ("CN", AQUA, "China")]
    ys = [[float(r[f"contrib_{k}"]) for r in retail] for k, _, _ in series]
    ax.stackplot(xs, *ys, colors=[c for _, c, _ in series], edgecolor=SURFACE, linewidth=1.5, alpha=0.95)
    shade_provisional(ax, retail, label=False)
    cum = [0.0] * len(xs)
    for (k, c, name), y in zip(series, ys, strict=True):
        mid = cum[len(xs) // 2] + y[len(xs) // 2] / 2
        ax.text(xs[len(xs) // 2], mid, name, color="#ffffff", fontsize=10, fontweight="bold", ha="center", va="center")
        cum = [a + b for a, b in zip(cum, y, strict=True)]
    ax.text(xs[0], 0.172, "Russia has no price source: weights are renormalised over EU, US and China", color=INK2, fontsize=9, ha="left", va="center")
    ax.set_ylim(0, 0.18)

    ax = axes[2]
    style(ax, "Wholesale index: EU day-ahead (USD per kWh, nominal). EU only: no other region has a reusable wholesale feed", "USD/kWh")
    wx = [d(r["month"]) for r in wholesale]
    wy = [float(r["level_usd_per_kwh"]) for r in wholesale]
    ax.plot(wx, wy, color=BLUE, linewidth=2)
    peak = max(range(len(wy)), key=lambda i: wy[i])
    ax.annotate(f"{wholesale[peak]['month']}  {wy[peak]:.3f}", (wx[peak], wy[peak]), xytext=(12, 0), textcoords="offset points",
                color=INK, fontsize=9, va="center")
    ax.text(wx[-1], wy[-1] + 0.02, f"{wholesale[-1]['month']}  {wy[-1]:.3f}", color=INK, fontsize=9, ha="right")
    fig.text(0.01, 0.006, "Four Corners Index, build of 2026-09-29. Sources: Eurostat, EIA, Ember (CC-BY-4.0), ECB (cross-rates are modified data),\n"
             "Shanghai Development and Reform Commission notice (China, low confidence). Not a forecast, not advice.", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    out = ROOT / "evidence" / "G4" / "index_chart.png"
    fig.savefig(out, dpi=110, facecolor=SURFACE)
    print("wrote", out.relative_to(ROOT), out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
