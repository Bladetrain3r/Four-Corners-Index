# Air quality tab: source scouting (2026-10-01)

*Scouting only, in the style of G1: nothing is built, nothing is on the site. Facts below were read from the pages cited on 2026-10-01; what I could not confirm says so. Ziggy asked for "an air quality index, as its own tab with sources" (earlier, 2026-09-29: "air quality indicators maybe" instead of carbon).*

## The short version
- **Recommended v1: the World Bank's "PM2.5 air pollution, mean annual exposure" (`EN.ATM.PM25.MC.M3`).** One consistent, modelled, population-weighted metric for **all six regions** (EU, US, China, Russia, South Africa, UK), 1990 to **2023**, from the same keyless JSON API family we already use. The page states `License: CC BY-4.0`. Latest values (2023, µg/m³): China 32.0, South Africa 27.7, Russia 11.6, EU 11.0, UK 9.5, US 7.0.
- **It is annual with a lag of about two and a half years, and modelled, not measured at a station.** It cannot be a monthly index like the other two without inventing something. Recommendation: a **tab** (annual series, per region, with a comparison to the WHO guideline and, from data we already hold, the fuel mix beside it), not a third headline index.
- **The upstream is IHME's Global Burden of Disease 2023 (GBD) estimates** (the World Bank cites it as the source, with the note "Need to create account to retrieve data"). The World Bank labels its copy CC BY-4.0. I could not read IHME's own terms (their page returned 403), and IHME has historically published GBD under non-commercial terms; this is the one real licence risk, to decide before building.

## Candidates, verified or not
| Source | Coverage | Access | Licence (what I read) | Fit |
|---|---|---|---|---|
| **World Bank WDI `EN.ATM.PM25.MC.M3`** | all six, annual to 2023 | keyless JSON, same API as the Pink Sheet adapter's host | indicator page: "CC BY-4.0"; WB default "CC-BY 4.0, with the additional terms" and third-party datasets "labeled accordingly"; upstream IHME terms **unread** | **v1** |
| CAMS global reanalysis (EAC4), monthly | global grid, 2003 to 2025, 4 to 6 months lag, twice a year | Atmosphere Data Store; GRIB or netCDF only, 0.75°; account needed (not stated on the page I read) | page: "CC-BY licence" (ECMWF forum: CC-BY replaced the Copernicus licence on 2025-07-02) | good monthly model, but **GRIB/netCDF cannot be read with the standard library**, and the pipeline is stdlib-only by rule; it would need a pinned dependency or a pre-aggregation step. A later option. |
| US EPA AirData files | US monitors, annual and daily CSV zips, no key | `annual_conc_by_monitor_YYYY.zip`, `daily_88101_YYYY.zip` | page states no reuse terms (US federal data is normally public domain; **I would want the sentence before relying on it**); updated twice a year (May, November), up to 6 months reporting lag | good US ground truth for v2 |
| EEA Air Quality Download Service | EU monitors from 2013 | API, zipped **Parquet** | licence not stated on the page I read | Parquet is not stdlib-readable; needs a CSV route or a dependency. v2 at best |
| UK-AIR (DEFRA) | UK | not fetched | I expect the Open Government Licence (unverified) | v2 candidate |
| OpenAQ v3 | global, aggregated | **API key required** | data under each provider's licence, attribution to OpenAQ and the original source; users may not build a service that duplicates OpenAQ's own | China coverage and the terms behind it are unclear; not for v1 |
| China CNEMC (national monitoring centre) | China | **no public download interface** (ESSD paper); technical limits per OpenAQ's landscape report | no reuse terms found | no source; consistent with the Retail card for China industrial |
| WHO Ambient Air Quality Database | city-level, 2 to 3 yearly | files | licence **not confirmed** (I suspected non-commercial, could not verify) | not for v1 |

Russia and South Africa have no open ground-monitor source I can reuse; only the modelled series covers them, which is a second reason for it as v1.

## What the tab would hold (v1 proposal, to be re-planned as G7)
1. A card per region: latest mean annual PM2.5 exposure, its year, its source and licence line, the quality badge (modelled, so B, and "low confidence" is not the right word: it is a model estimate, labelled so).
2. A 1990 to 2023 line per region, direct labels, "view as table", downloads CSV and JSON.
3. A reference line for the WHO annual guideline (I believe 5 µg/m³ in the 2021 guidelines; to be verified from WHO's own page at build time, never taken from memory).
4. The fuel mix we already hold (coal and gas share, Ember) beside each region's PM2.5, with the caution in plain words that power generation is one of several sources and the two are not shown as cause and effect.
5. The sources page gets its entry (attribution in the form the licence asks: World Bank, IHME GBD 2023, "modified" statement for any conversion).

## Questions for Ziggy
1. **Annual, modelled PM2.5 as v1, as a tab not a third index?** (Alternative: wait for a monthly model such as CAMS, which means a dependency.)
2. **Licence comfort with the IHME upstream:** the World Bank page says CC BY-4.0, and the attribution would name IHME; I could not read IHME's own terms. Earlier you chose "play it safe" for Eskom and "sanitise later" for a lesser question. Which here?
3. **Ground monitors later (v2: US EPA, UK, EU) or never?** They add measured values for three regions only, at the price of two new file formats or dependencies.
4. **A dependency exception?** The stdlib-only rule is what keeps the pipeline readable; GRIB or Parquet would break it. I recommend not, for now.
