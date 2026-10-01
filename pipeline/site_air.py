"""The air quality tab's data: PM2.5 exposure per region, the WHO guideline, and the fuel mix of the same year (site/data/air.json)."""
from __future__ import annotations

from typing import Any

from pipeline import site_data

SERIES = "worldbank__wdi_pm25"
SERIES_ID = "worldbank:wdi:EN.ATM.PM25.MC.M3"
CLEAN = ("nuclear", "hydro", "wind", "solar", "bioenergy", "other_renewables")


def annual_mix() -> dict[tuple[str, int], dict[str, float]]:
    """(region, year) -> shares of coal, gas, other fossil and clean in annual generation, for years with twelve complete months only."""
    tot: dict[tuple[str, int], dict[str, float]] = {}
    months: dict[tuple[str, int], set[str]] = {}
    for r in site_data.series_rows("ember__monthly_generation"):
        if r["series_id"] != "ember:monthly:generation":
            continue
        key = (r["region"], int(r["period_start"][:4]))
        tot.setdefault(key, {})
        tot[key][r["fuel"]] = tot[key].get(r["fuel"], 0.0) + float(r["value"])
        if r["fuel"] == "total":
            months.setdefault(key, set()).add(r["period_start"][:7])
    out = {}
    for key, t in tot.items():
        if len(months.get(key, ())) != 12 or t.get("total", 0) <= 0:
            continue
        total = t["total"]
        out[key] = {"coal": t.get("coal", 0.0) / total, "gas": t.get("gas", 0.0) / total, "other_fossil": t.get("other_fossil", 0.0) / total,
                    "clean": sum(t.get(f, 0.0) for f in CLEAN) / total, "total_twh": total}
    return out


def air_doc() -> dict[str, Any]:
    facts = site_data.manual("air_quality.json")
    common = {"indicator": facts["indicator"], "guideline": facts["guideline"], "method": facts["method"], "badge": facts["badge"], "badge_note": facts["badge_note"]}
    try:
        pts = site_data.series_rows(SERIES)
        m = site_data.meta(SERIES)
    except FileNotFoundError:
        return {"status": "not_yet", **common,
                "reason": "This series has not been fetched yet: the daily run adds it the first time it runs after this page is deployed."}
    regions_meta = site_data.manual("regions.json")["regions"]
    mix = annual_mix()
    by: dict[str, dict[int, float]] = {}
    for p in pts:
        if p["series_id"] == SERIES_ID:
            by.setdefault(p["region"], {})[int(p["period_start"][:4])] = float(p["value"])
    guideline = facts["guideline"]["value"]
    regions = []
    for reg in regions_meta:
        rid = reg["id"]
        vals = by[rid]
        year = max(vals)
        mx = mix.get((rid, year))
        regions.append({"id": rid, "name": reg["name"], "short": reg["short"], "note": facts["regions"][rid]["note"],
                        "latest": {"year": year, "value": vals[year], "times_guideline": vals[year] / guideline},
                        "series": [{"y": y, "v": v} for y, v in sorted(vals.items())],
                        "mix": ({"year": year, "coal": mx["coal"], "gas": mx["gas"], "other_fossil": mx["other_fossil"], "clean": mx["clean"], "total_twh": mx["total_twh"]}
                                if mx else None)})
    newest = max(r["latest"]["year"] for r in regions)
    return {"status": "value", **common, "as_of": m["as_of"], "retrieved": m["retrieved_at"][:10], "raw_sha256": m["raw_sha256"], "newest_year": newest, "regions": regions,
            "gap_note": f"No value is published for {newest + 1} onward: the World Bank has not released them yet, so none is shown.",
            "mix_note": "Ember annual generation shares for the same year (twelve complete months), computed from the monthly data on this site."}
