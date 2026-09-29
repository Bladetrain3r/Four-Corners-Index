# Method — Four Corners Index

*Version 2. Version 1 was written and frozen 2026-09-30 at the start of G4, **before any index value was computed** (the commit order shows it: that commit precedes every file that computes an index); version 2 was committed before any value it adds (the ex-China variant). A change to anything below is a new version with a dated entry in "Changes"; earlier versions stay in git history. Decisions marked **Ziggy** are his (STOP-1 answers, 2026-09-29); everything else is the builder's, logged in `LOG.md`.*

Two monthly indices, in nominal US dollars per kWh: the **Retail index** (household prices) and the **Wholesale index** (day-ahead prices). Each value can be re-derived from the kept raw snapshots by `python -m pipeline.build`; see "Reproducibility".

## 1. What goes in

| Index | Regions included | Series | Source |
|---|---|---|---|
| Retail | EU | household, band DC (2,500–4,999 kWh/yr), all taxes and levies (`I_TAX`), EU-27 aggregate, semi-annual | Eurostat `nrg_pc_204` |
| Retail | US | residential average price (all residential customers, not a consumption band), monthly | EIA `retail-sales`, sector RES |
| Retail | China | first-tier household tariff of **Shanghai** (0.617 CNY/kWh, per its 2012 notice), an administrative price, badge C, tier `low_confidence` | `data/manual/china_household_tariff.json` (dated fact, source URL and SHA-256 recorded) |
| Wholesale | EU | day-ahead price per country, load-weighted monthly average, aggregated to EU-27 (section 5) | Ember (CC-BY-4.0), from ENTSO-E |

**Not included, and why** (each is shown on the site as "no source" with its reason): Russia, every layer (no reusable source; Rosstat and ATS unreachable, Bank of Russia terms restrict reuse); South Africa price layers (Eskom terms bar commercial reuse and crawling; Ziggy: drop) and it is beside the basket, not in it; US, China and Russia wholesale (no reusable market feed); EU carbon price (no free reusable source; Ziggy: out). The United Kingdom, if added, is beside the basket (Ziggy: a good option; source check pending) and not in either index.

**Comparison series, not in either index** (highlighted as such on the site): EU non-household band IC (500–1,999 MWh/yr), Eurostat's own headline band, beside our headline band ID (2,000–19,999 MWh/yr, excluding VAT and recoverable levies, `X_VAT`); Guangdong first-tier tariff (67.02 fen/kWh from 2021-12, low confidence). Industrial prices are shown on the regional pages; there is no Industrial index at launch.

## 2. Weights

w(r, y) is region r's share of the **Ember yearly Demand** (Ziggy: Ember) of calendar year **y − 1**, among the four basket regions EU, US, China and Russia (all four are in the denominator whether or not a price exists), fixed for calendar year y. Ember's Demand follows inland demand (G3 evidence: 4.1% above Eurostat inland demand, 15.0% above final consumption). For the calendar year y the latest complete year is y − 1; a 2026 month uses 2025.

Because Russia has no price, the weights are **renormalised over the regions that have a value that month**: w'(r, m) = w(r, y) / Σ w(s, y) over the included regions s. The renormalisation and the resulting composition are published with every value (`composition`).

**Rule (from G3, Ziggy-approved): weights use Ember's yearly Demand. Ember's monthly series are used only for generation shares and carbon intensity, never mixed with yearly levels.** Ember's monthly and yearly files disagree in coverage for every area but the US (`evidence/G3.md`).

**Equal-weighted variant** (Ziggy: shown on the headline page): w'(r, m) = 1 / n over the same included regions.

## 3. Prices and currency

- p(r, m), region price in USD/kWh, is the local price converted at the **monthly average FX rate** of month m (nominal, the currency of the time; Ziggy, SPEC decision 4). Inflation adjustment is out of scope.
- FX source: ECB euro reference rates, monthly average (`M` series), currency units per euro. EUR→USD is the USD rate. CNY→USD is the cross rate (CNY per EUR) ÷ (USD per EUR). **Cross rates and conversions are modified data and are labelled so** (ECB terms).
- Wholesale: EUR/MWh ÷ 1,000 × USD per EUR.
- Rounding: USD/kWh values are stored and hashed to 6 decimal places, index numbers to 3, using decimal arithmetic on the rounded inputs; nothing is rounded twice.

## 4. The indices

- **Retail index level** R(m) = Σ w'(r, m) · p_household(r, m) over the included regions. **Wholesale index level** W(m) = Σ w'(r, m) · p_wholesale(r, m); with only the EU included its weight is 1 and W(m) is the EU wholesale price. The site labels it **EU wholesale** (Ziggy, STOP-1 decision 1).
- **Index form (2015 = 100):** I(m) = 100 · L(m) / L̄₂₀₁₅, where L̄₂₀₁₅ is the mean of that index's twelve monthly levels of 2015 (of the same definition and composition as published for 2015). Levels are published beside it.
- **Contributions:** each region's contribution is w'(r, m) · p(r, m); they sum to the level.
- **Retail excluding China (variant, version 2; Ziggy, after STOP-2):** the same construction over EU and US only: w'(r, m) = w(r, y) / (w(EU, y) + w(US, y)) for r in {EU, US}, weights from the same Ember Demand shares (China and Russia stay in the denominator of w, then are dropped in the renormalisation). Level, index form (2015 = 100 over its own 2015 months) and contributions are published beside the headline on the headline page. It is a variant like the equal-weighted one: **not** a ledger series, and it shares the headline's provisional or final status for the month. Its purpose is to show the part of the Retail index that rests on measured prices rather than on one administrative tariff (section 11).
- **Coverage:** monthly from 2015-01 to the latest month for which every included region has a value (observed or carried forward as below).

## 5. EU wholesale aggregate

For month m in year y: the EU value is the demand-weighted mean of the Ember country day-ahead monthly prices of the **EU-27 member states** that have a price in m, weighted by Eurostat `nrg_cb_e` **inland demand (ID)** of year y − 1, renormalised over the countries present. Countries outside the EU-27 (Norway, Switzerland, the United Kingdom, Serbia, Montenegro, North Macedonia, Albania) are excluded. Cyprus and Malta have no Ember price and Bulgaria, Croatia and Ireland start later (2016-10, 2017-10, 2018-10); the composition (`countries`) and the share of EU inland demand covered are published with every value. The current month of Ember's file is a partial running average and is **never published as final**.

## 6. Missing and lagging inputs; provisional and final

- A source publishes a value for a **period** (semester, month). Every month inside the period takes the value. EU household: a semester value applies to its six months.
- **Carry forward.** If a region's value for a month is not yet published, the last published value is carried forward and the month is **provisional**, for at most 12 months (EU household, semi-annual); US at most 3 months; China's administrative tariff is valid until superseded and is carried indefinitely, flagged with the date it was last confirmed (2026-09-29). Beyond the limit the region drops out of that month's composition, and the month is provisional and says so. Carried values never replace a later published value: on arrival the month is revised (below).
- **Provisional inputs.** An input value is *provisional* if it is carried forward, or is a US EIA monthly price less than 12 months old (EIA's Electric Power Monthly calls the latest values "preliminary estimates"; the 12-month window is a **builder assumption** to be tightened if EIA's revision policy is confirmed), or carries a publisher flag `p` or `estimate`. A month's index value is **final** only when every included input for that month is non-provisional; otherwise **provisional**.
- **Gaps** the publisher leaves empty are shown as gaps with their reason and are never interpolated; a region with a gap in month m is out of that month's composition.

## 7. Revisions and the ledger

Every published index value is one line in `ledger/index.jsonl`: `index`, `month`, `value_usd_per_kwh`, `index_2015_100`, `status`, `composition`, `method_version` (the version of the **headline** method that produced the value; adding a variant does not change it, so it stays 1 while the headline definition is unchanged), `published` (date), `inputs_sha256` (the SHA-256 of the raw snapshots used), `prev_hash`, `hash`. `hash` is SHA-256 over the canonical JSON (sorted keys, separators `,` and `:`, UTF-8) of the entry without `hash`; `prev_hash` is the previous line's `hash`, the first line's is `GENESIS`. A revision (a later publication changing a month's value or status) is a **new line** with `supersedes` = the `hash` of the line it replaces; earlier lines are never edited. `ledger/verify.py` recomputes the chain; tampering with any line, or with the order, makes it fail. Signing is out of scope.

The launch backfill (2015-01 to the latest month) is published on the build date and marked `backfill: true`.

## 8. Continuity checks (thresholds fixed before any value was computed)

Every month-on-month move in a headline index level above **4% (Retail)** or **20% (Wholesale)** in absolute value must have an explanation line in `checks/explained_moves.md`, or it is a defect. An explanation states the mechanism from data (the contribution of each region, and for each region whether the move came from the local price or from FX) and, where a real-world cause is named, cites a source we hold. The thresholds are wide on purpose for Wholesale, which is volatile by nature.

## 9. Nowcast (decision recorded)

**No nowcast at launch.** The EU household price arrives half-yearly and about nine months late, so recent months are carry-forward and provisional. A nowcast scaled by the Eurostat HICP electricity sub-index (`prc_hicp_minr`, ECOICOP v2) was considered and is deferred: its current dataset starts in 2020-01, chaining onto the frozen `prc_hicp_midx` across the classification change is untested, and HICP is an index, not a price per kWh. If added later (Ziggy: a separate line, never in "final"), it is a new method version.

## 10. Reproducibility

`python -m pipeline.build --raw raw_cache --out <dir>` reads only the raw snapshots listed in `data/manifests/raw_snapshots.jsonl` (each verified against its SHA-256), makes no network request, and writes byte-identical outputs on every run (`evidence/G4.md` compares hashes of two clean rebuilds with the network blocked). Raw snapshots are kept forever, append-only, as monthly GitHub Release assets with the manifest committed here. **Exception (Ziggy, 2026-09-30):** because no Release upload was possible from the build session, one gzipped archive of every snapshot in the manifest as of the 2026-09-29 snapshot is committed once as `snapshots/raw_2026-09-29.tar.gz`; `python -m pipeline.snapshot --restore` extracts it into `raw_cache/` and verifies every file against its manifest SHA-256. Further snapshots are uploaded as Release assets in a session that has a token; until then they live in `raw_cache/` (not in git).

## 11. Known limits (read before using a number)

- Household prices are not like-for-like: EU is a consumption band, US is the all-residential average, China is one city's first tier of a tiered administrative tariff.
- **China carries the largest weight (about 59% once Russia drops out) and the weakest data**: one constant tariff in yuan (per Shanghai's 2012 notice; whether it has been re-issued since is not confirmed) converted at a moving exchange rate. Over 2015–2025 the China contribution moves only with CNY/USD. The equal-weighted variant and the contribution panel are on the headline page for this reason (Ziggy, STOP-1 decision 4).
- EU retail lags about nine months; recent months are provisional by construction.
- Wholesale is EU-only.
- Not a coin, a forecast or advice.

## Changes
- 2026-09-30, version 1: first version.
- 2026-09-30, version 2: adds the Retail-excluding-China variant (section 4); records the one-off snapshot archive committed to git (section 10); clarifies that the ledger's `method_version` is the headline method's. No headline value changes.
