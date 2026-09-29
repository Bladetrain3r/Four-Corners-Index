# Four Corners Index — specification

*See `SOURCES.md` "What the research changed" for the data realities behind this table. Written 2026-09-29 by the conductor (Ziggy's fleet) from Ziggy's decisions of the same day. This file is the
what; `GATES.md` is the order and the pass/fail; `CLAUDE.md` is how the building session works. Changing a
decision marked **Ziggy** needs his word (a STOP point); everything else is the builder's judgment, logged.*

## Purpose

A public dashboard of what electricity actually costs, across the four largest economic blocs by electricity use,
with South Africa shown beside them. The dashboard shows what a kWh costs, what it is made of, and why it moves. Two
indices are the headline. Everything shown can be re-derived from the kept sources by anyone who clones the repo.

Not a coin, not a token, not a forecast, and not advice. The index is a published number with a published
method. It exists as a unit of account for readers (and later for the fleet's own accounting).

## Decisions (Ziggy, 2026-09-29)

1. **Two indices, not one blend.** The **Retail index** (what households pay; "the index") and the **Wholesale index**
   (the day-ahead market price, where a market exists) are shown side by side. They differ several-fold and move
   for different reasons, and blending them would hide both.
2. **Consumption-weighted basket.** Each region's weight is its share of total annual electricity consumption
   across the four. An equal-weighted variant is available one click down, never as the headline.
3. **Basket: EU, US, China, Russia.** **South Africa is shown beside the basket and is not in it.**
4. **Nominal prices only at launch:** the price at the time, in the currency of the time, converted at that
   period's exchange rate. Inflation adjustment ("real") is a later toggle, not in scope.
5. Price per **kWh**, never "per watt".

## Decisions (Ziggy, STOP-1, 2026-09-29)

6. **Wholesale index is EU-only and labelled so.** Other regions show "no source" and the reason.
7. **Weights come from Ember Demand** for all regions. **The equal-weighted variant and contribution by region are on the headline page**, not one click down (this supersedes "one click down" under Visible metrics).
8. **Confidence tiers.** Sourced bands are the headline. Low-confidence or high-latency equivalents are included where possible, highlighted as such (`confidence`: `primary`, `low_confidence`, `high_latency`).
9. **Russia is high-uncertainty**, flagged on every figure. Secondary sources are allowed only where their terms permit reuse and the number traces to a kept snapshot; otherwise "no source".
10. **South Africa** keeps only the layers with a public licence (mix and carbon intensity, coal, FX). Eskom tariffs are not used: their terms bar commercial use and automated collection. A publicly licensed tariff source would bring the price layers back.
11. **No carbon (EUA) price.** Omitted and said so on the site.
12. **Candidate layer, not built:** air-quality indicators (needs its own scoping and source check first).
13. **Nowcast** (if any) is a separate line, never in "final"; decided at G4: none at launch (METHOD.md section 9).
14. **United Kingdom beside the basket** (Ziggy: "I think the UK might be a good option"). Not in either index and not weighted. DESNZ QEP tables 5.6.2 and 5.4.2 use Eurostat's own household band DC and non-household band ID, so it is like-for-like with the EU series; all under OGL v3.0. Source check 2026-09-29 (SOURCES.md Part F); adapters follow G4.

## The three layers (what is tracked)

**1. Cost: what a kWh costs, by buyer type**
- Household (retail, taxes included, in a typical household consumption band)
- Industrial / non-household (taxes excluding VAT and recoverable levies, in a typical mid-size band)
- Wholesale: the day-ahead market average; "no market" is shown as such (South Africa; parts of China/Russia)
- Price components where the source provides them (EU: energy and supply, network, taxes and levies)

**2. Mix: what it is made of**
- Generation share by type: coal, gas, oil, nuclear, hydro, wind, solar, bioenergy, other
- Carbon intensity, gCO₂ per kWh generated
- Total generation and demand

**3. Drivers: why it moves**
- Natural gas: European hub (TTF) and US Henry Hub
- Coal (a benchmark including South African coal if a free source carries it)
- EU carbon (ETS) price: omitted, no free reusable source (G1; decision 11)
- FX to USD: EUR, CNY, RUB, ZAR

## Regions

| Region | In basket | Retail | Industrial | Wholesale | Mix | Data quality badge |
|---|---|---|---|---|---|---|
| EU (EU-27 aggregate; drill-down DE, FR, IT, ES, PL, NL) | yes | yes | yes | yes (per bidding zone, aggregated) | yes | A |
| US (national; states later) | yes | yes | yes | hubs, if a free series exists | yes | A |
| China | yes | best effort (provincial catalogue basket) | best effort | none nationally (say so) | yes | C |
| Russia | yes | best effort (Rosstat household) | no source found yet | two price zones, if reachable | yes | C |
| South Africa | **beside** | no source (Eskom terms; decision 10) | no source (decision 10) | no market (say so) | yes | B (mix only) |

Badges: **A** is an official, machine-readable, regularly published source. **B** is official but tariff-derived or
partly manual. **C** is best effort: administrative prices, irregular publication or hard access; shown with its
caveat. A missing value is shown as a gap with the reason, never interpolated silently.

## Visible metrics

**Headline, above the fold**
- Retail index and Wholesale index: the latest value (USD per kWh, toggle to EUR and ZAR), month-on-month and year-on-year
  change, status **provisional** or **final**, the publication date
- One card per region: household, industrial and wholesale price, each with its **as-of date** and source (the
  sources lag differently; every figure carries its age), plus the quality badge
- One card per region for mix and carbon: a stacked share bar and gCO₂/kWh
- Drivers strip: gas, coal, carbon and FX sparklines (12 months)

**One click down**
- Per-region pages: long series, buyer-type comparison, price components (EU), mix over time, the sources used
- Index page: the method, weights by year, and the revision ledger (the equal-weighted variant and contributions by region are on the headline page, per decision 7)
- Downloads: every published series as CSV and JSON, plus the raw-snapshot manifest

## Index method (outline; `METHOD.md` is written and frozen at G4 before any index is computed)

- Monthly. Region price p(r,m) in USD/kWh at month m's average FX rate. Weight w(r,y) is the region's consumption
  share in the latest complete year available at publication (fixed for the calendar year, stated on the page).
- Retail index = Σ w·p(household). Wholesale index = Σ w·p(wholesale) over the regions that have a market, with
  weights renormalised over those regions and the renormalisation stated.
- When a region's month is missing (lagging source), carry the last value forward and mark the month
  **provisional**. When all inputs are final, the month is marked **final**. A revision after that is a new
  ledger entry, never an overwrite.
- Semi-annual or annual sources (EU retail, tariffs) apply to every month in their period. An optional monthly
  nowcast (for example, EU retail scaled by the HICP electricity sub-index) is decided at G4 and, if used, is shown
  as a separate line, never mixed into "final".
- Levels are published in USD/kWh; an index form (2015 = 100) is shown beside the levels.

## Retention

- **Monthly series from 2015-01** on the site (earlier data downloadable where sources have it).
- **Hourly and daily data** (wholesale prices, generation mix): full resolution for a rolling 2 years on the site;
  daily and monthly roll-ups kept forever.
- **Raw source snapshots are kept forever**, append-only: stored as monthly GitHub Release assets (compressed),
  with a SHA-256 manifest committed in the repo. The repo itself holds code, normalised series and manifests, and
  stays small (a size budget is checked in CI).
- **The ledger:** every published index value is a line in `ledger/index.jsonl`, hash-chained (each entry carries the
  previous entry's hash). Revisions are new lines that name the value they supersede. Signing (for example Sigstore
  in Actions) is a later step, not in scope.

## Update cadence

- **One scheduled pipeline run daily** (GitHub Actions). Each source is fetched on its own cadence; a source whose
  data has not changed produces no commit.
- **Daily panels:** wholesale prices, generation mix, gas, FX.
- **Monthly publication of both indices on a fixed day, the 15th**, for the previous month, provisional until the
  slowest input lands, then final.
- **Source health:** a source that fails, or changes shape, turns the run red and opens a GitHub issue naming the
  source and the failing check; the site shows that source's last good date.

## Build constraints

- Python 3.12 for the pipeline, minimal dependencies (stdlib first; pandas only if it earns its place, and the
  choice is logged), pytest.
- **The site is static:** plain HTML, CSS and JS, with data read from JSON files, one charting library (ECharts or uPlot,
  pinned version), and no build step unless one earns its place. It is served by GitHub Pages and works at phone width.
- **No secrets in the repo.** API keys arrive as environment variables (GitHub Actions secrets in CI; the build
  environment's variables in the session). With a key absent, the pipeline runs from committed fixtures and says so.
- **Attribution for every source**, in the footer and on the sources page, in the form the source's licence asks for.
- **Licence of the code:** MIT (Ziggy, 2026-09-29; `LICENSE`). Data carries its sources' terms, stated per source.
- **Public from the start** (Ziggy, 2026-09-29): the repo is public; Pages is switched on by Ziggy at STOP-3.
- **Sponsorship:** this project is the pilot for Ziggy's GitHub Sponsors profile. The site gets a small "Sponsor" link in the footer
  and `.github/FUNDING.yml` is added **only once the profile is live** (live 2026-09-29, github.com/sponsors/Bladetrain3r;
  FUNDING.yml added the same day; the footer link is the builder's at G5) (Ziggy says so; never link a profile that does not
  exist). There is no paywall, no gated data, and no sponsor influence on the numbers or the method, and the site says that in one line.

## Out of scope (for this build)

Inflation adjustment, US state and Chinese provincial drill-downs, forecasts, alerts to readers, accounts, a
backend server, signing, and any token or on-chain component.
