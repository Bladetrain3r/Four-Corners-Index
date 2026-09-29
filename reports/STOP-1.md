# STOP-1 — sources verified (G1)

*2026-09-29. Read `SOURCES.md` for the evidence and `evidence/G1.md` for the checks. This report is the decisions I need from Ziggy. Answer in this file (a commit) or in a PR comment. Nothing past G1 has been started.*

## The short version

- **Retail is real for the EU and the US, weak for China, blocked for Russia, tariff-derived for South Africa.**
- **The Wholesale index is EU-only.** No other region has a reusable, reachable wholesale price. Section 1 asks how to label it.
- **China carries 55.3% of the consumption-weighted Retail index and is the weakest price data we have.** Section 4 says what that does to the headline.
- **The only key needed is the EIA one, which is set.** ENTSO-E is not needed: Ember carries the EU day-ahead prices under CC-BY.
- 36 source entries in `SOURCES.md`, 11 fixture directories, all manifests pass, 17 tests pass locally (CI was green at G0; the G1 push is checked below).

## Source map

Household and industrial are my proposals; badges per SPEC. Full detail is in the region map at the top of `SOURCES.md`.

| Region | Household | Industrial | Wholesale | Mix | Weights |
|---|---|---|---|---|---|
| EU (A) | Eurostat `nrg_pc_204`, band DC (2,500–4,999 kWh/yr), all taxes, `EU27_2020`, latest 2025-S2 | `nrg_pc_205`, band ID (2,000–19,999 MWh/yr), excl. VAT and recoverable levies (`X_VAT`) | Ember (CC-BY), per country from 2015-01; we build the EU aggregate | Ember (from 2016-01) | Ember Demand |
| US (A) | EIA retail, residential average | EIA retail, industrial average | **no source** (see 1) | EIA or Ember, one of them | Ember Demand |
| China (C) | First-tier household tariff, provincial basket (Shanghai, Guangdong verified) | Agency-purchase price for default-supply C&I users (Henan, Guangdong verified) | none, no national market | Ember | Ember |
| Russia (C) | Rosstat per-100-kWh, **blocked** (see 3) | **no source** | **no source** | Ember | Ember |
| South Africa (B, beside) | Eskom Homelight 20A, plus Eskom residential realised average | Eskom industrial (excl. NPA) realised average | no market | Ember | Ember |

Drivers: gas from the World Bank Pink Sheet (CC BY 4.0, TTF from 2015-04) and EIA Henry Hub; coal from the Pink Sheet; FX from the ECB (USD, CNY, ZAR); **EU carbon: no source**; **RUB: see 3**.

## Decisions needed

### 1. Wholesale index scope (blocks the headline)
Only the EU has a usable wholesale source. Checked and rejected for the US: EIA hub files are ICE data "republished, with permission"; of the seven ISOs, only CAISO and ERCOT publish under terms that clearly allow reuse, and their keyless history is 39 months and 31 days. NYISO has good history (from 2000) but grants no licence. MISO's terms were behind a challenge page. ISO-NE, PJM and SPP prohibit or restrict redistribution.
- **A (my recommendation):** publish it as **"EU wholesale"**, one region, labelled as such on the site and in `METHOD.md`, with the US, China, Russia and South Africa shown as "no source" and the reason. It is honest and it is still useful.
- **B:** hold the Wholesale index back until a US source clears. You would ask NYISO (and MISO) for written permission; I will not.
- **C:** an ERCOT + CAISO composite. Two of seven ISOs, no PJM, no history before 2023-07. I would not publish it as "US".

### 2. Consumption weights source (blocks G4, shapes G2)
Recommend **Ember Demand for all five regions**: one definition, machine-readable, CC-BY, 2025 values in the fixtures. Cross-check at G3 against Eurostat `nrg_cb_e` (EU 2025, provisional: Eurostat final consumption 2,412 TWh and inland demand 2,664 TWh, against Ember Demand 2,774 TWh; which Eurostat definition Ember's "Demand" follows is **not confirmed**, and that gap is 4–15% for the EU weight), NEA (China) and SO UPS (Russia 1,177.3 vs Ember 1,177.3, which agree). EIA retail sales (4,058 TWh) is a different concept from Ember's US Demand (4,532 TWh); do not mix.

2025 weights over the four basket regions (computed from Ember Demand: China 10,486, US 4,532, EU 2,774, Russia 1,177 TWh; total 18,970 TWh):
**China 55.3% · US 23.9% · EU 14.6% · Russia 6.2%.** South Africa (236.8 TWh) sits beside the basket and is not weighted.

### 3. Russia: three separate blockers (your calls)
1. **Rosstat household price:** `rosstat.gov.ru` is served with a certificate from the Russian national CA, which the environment does not trust. I did not bypass it. Options: pin that CA for that one host only, in the adapter and in CI (your security call), or mark Russia household as "no source".
2. **RUB to USD:** the ECB stopped its RUB rate on 2022-03-01. The Bank of Russia rate is reachable and keyless, but its user agreement reads "Materials of the Website may only be used with the consent of the rightsholders" and requires a link. Options: use it with a link and attribution, and treat the risk as yours; ask the Bank of Russia; or leave Russia out of USD terms.
3. **Industrial and wholesale:** no source found (ATS unreachable, cause not proven; no industrial series).
If Russia has no household price, the Retail index would be EU, US, China renormalised. I recommend the site says so on every month the composition differs, or that we accept the composition change and state it once in `METHOD.md`. Tell me which.

### 4. China's weight versus China's data quality
China is 55.3% of the headline and rests on a basket of two verified provinces' first-tier tariffs (2012 and 2021 notices, unchanged until a province reissues), on a 12-month step function. That makes the consumption-weighted Retail index largely a proxy for the Chinese first-tier tariff. Options:
- **A (recommended):** publish as designed, badge C on China, and show the **equal-weighted variant** and a "contribution by region" panel on the headline page, not one click down, so readers can see the dependence.
- **B:** cap China's weight or use a floor for a lower-quality badge. It changes your decision 2, so it needs your word.
- **C:** exclude China until better data exists. Also changes decision 3 (basket).
Also the industrial China series (default-supply C&I only) is fragile to discover monthly (PDFs on city mirrors). I would use it only at annual resolution in the index, and show it separately.

### 5. South Africa and Eskom's terms
Eskom's site terms bar commercial use and automated collection without written consent (clauses 2.2, 2.10; contact `electricitypricing@eskom.co.za`). The tariff workbook is machine-readable, annual, and fine for a manual yearly load. Options: ask Eskom for consent (your act), or load the figures manually each April with a quotation and a link and no crawler. Which? South Africa is beside the basket, so this does not block the indices.

### 6. Carbon price: **out**
No free, reusable EUA series exists. EEX auction files download keyless but are not open-licensed (their disclaimer requires written approval for commercial use; their "Media Usage" licence allows public tickers). Recommend: omit and say so on the site. If you want it in, ask EEX for permission or the Media licence.

### 7. Eurostat retail lag and the nowcast
EU retail is nine months stale (2025-S2 today). The HICP electricity series starts 2020-01 in its current dataset; older data is in frozen datasets that still answer with stale data ending 2025-12. Recommend the nowcast, if used, is a **separate line** chained from the last level, never in "final" (as the SPEC says), and that we decide at G4. Say now if you would rather not have one.

### 8. Band choices
As in the table. Note the US series are averages over all customers of the sector, not a typical-consumption band, so EU and US household are not like-for-like. `METHOD.md` will say so. Confirm the EU bands (household DC, non-household ID with `X_VAT`) or give me others.

### 9. Housekeeping
- **Keys:** `EIA_API_KEY` only (in the session; you said it is in Actions too). The EIA API intermittently returns HTTP 500 on valid requests (5 of 18 calls); adapters will retry with backoff.
- **Release-asset upload** needs a token with write access to Releases. In Actions the default `GITHUB_TOKEN` with `contents: write` covers it. I cannot test it from the session, so G6 will say it is unproved until the first real run.
- **Hosts unreachable from this environment** (I did not work around any): `rosstat.gov.ru`, `gks.ru`, `atsenergo.ru`, `np-sr.ru`, `fedstat.ru`, `data.stats.gov.cn`, `cec.org.cn`, State Grid and China Southern Grid provincial sites, `jgs.ndrc.gov.cn`, several provincial DRCs, `statssa.gov.za`, `dataservices.imf.org`, `carbonpricingdashboard.worldbank.org`, `www.eia.gov/opendata/bulk/` (index page only). The daily GitHub Actions runner may see different results, particularly for Chinese and Russian hosts.
- **Attribution wording** I intend to use: Eurostat ("Source: Eurostat, dataset code, access date"), Ember ("Ember, CC-BY-4.0"), EIA ("Source: U.S. Energy Information Administration"), World Bank ("The World Bank: Commodity Price Data (The Pink Sheet)"), ECB, IMF if used. Modified data (our USD conversions and cross-rates) is labelled as modified.

## What I would do next (G2), if you say go
One adapter per source in `pipeline/`, each parsing its committed fixtures into the common schema, with a corrupted-fixture test that fails loudly naming the source. Order: Eurostat, EIA, Ember, ECB, World Bank, then the Eskom and China tables. No adapter for anything you rule out above.

## Process note (for the owner)
Five research agents ran in parallel for G1 and produced 570+ lines of drafts. The evaluation that mattered was mine, after assembly: `test_sources_doc.py` failed twice on real gaps (a China fixture cited only by shorthand, and 11 entries with no per-entry check date, 4 with no licence line) that reading the drafts had not shown. Details in `LOG.md`.
