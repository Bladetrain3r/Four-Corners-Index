# Sources

*Re-verified from the build environment on 2026-09-29 (G1). Every entry below was read from a live response or an official page that day; anything not read is marked "not confirmed". This replaces the desk research of the same date (it stays in git history at commit 1e6affb). Fixtures with URL, fetch time and SHA-256 are in `fixtures/<source>/MANIFEST.json`, and `python checks/verify_fixtures.py` checks them. Nothing here is a number the build invented.*

## Region and layer map (SPEC's region table → source)

"Household" and "industrial" are proposals for Ziggy at STOP-1; badges A/B/C per SPEC.

| Region | Household (retail) | Industrial | Wholesale | Mix and carbon | Consumption (weights) |
|---|---|---|---|---|---|
| **EU** (A) | Eurostat `nrg_pc_204`, band DC 2,500–4,999 kWh/yr, `I_TAX`, `EU27_2020`, semi-annual, latest 2025-S2 | Eurostat `nrg_pc_205`, band ID 2,000–19,999 MWh/yr, `X_VAT` (excl. VAT and recoverable levies), same cadence | Ember European wholesale prices (CC-BY; day-ahead from ENTSO-E), per country monthly from 2015-01; **no EU aggregate row, so we build one** (weights needed) | Ember monthly (EU from 2016-01) | Eurostat `nrg_cb_e` (2025 provisional) or Ember Demand (one source for all five, see open question) |
| **US** (A) | EIA `retail-sales`, sector RES, monthly from 2001, latest 2026-07 (key) | EIA `retail-sales`, sector IND (average revenue per kWh, not a band price) | **No source.** EIA hub files are ICE data "republished, with permission" (not reusable). ISO data checked: only CAISO (about 39 months keyless) and ERCOT (about 31 days keyless) have clear reuse terms; NYISO and MISO have data but no licence; ISO-NE, PJM, SPP blocked (Part D) | EIA `electric-power-operational-data` (utility-scale only) or Ember (includes small-scale solar); choose one | Ember Demand (4,532 TWh 2025); EIA retail sales quantity is a different concept |
| **China** (C) | First-tier household catalogue tariff for a documented provincial basket; verified reachable: Shanghai 0.617 (2012 notice), Guangdong 0.6702 (2021 list). Level changes only when a province reissues its notice | Agency-purchase all-in price (1–10 kV) for default-supply commercial and industrial users; Henan (Aug 2026) and Guangdong-Shantou (Apr 2026) verified as PDFs on city mirrors; monthly discovery is fragile; not an industrial average | **None** (no national market) | Ember monthly (from 2016-01) | Ember; NEA monthly release is a cross-check (Aug 2026: 1,033.2 bn kWh) |
| **Russia** (C) | Rosstat per-100-kWh household series, **not confirmed**: rosstat.gov.ru fails TLS verification here (Russian national CA). Needs Ziggy's decision | **No source** | **No source** (ATS unreachable from here; cause not proven) | Ember monthly (from 2019-01) | Ember; SO UPS 2025 consumption 1,177.3 bn kWh is a cross-check |
| **South Africa** (B, beside basket) | Eskom Homelight 20A 2026/27 235.04 c/kWh excl. VAT (270.30 incl.), annual, plus Eskom "Residential" realised average 273.79 c/kWh (2025/26). **Eskom terms require written consent for commercial use and crawlers** | Eskom "Industrial (Excl NPA)" realised average 212.03 c/kWh (2025/26); a Megaflex or Miniflex reference bill is a design choice | **No market** (NTCSA SAWEM page reads "Coming soon"; the 2026-04-01 date on it has passed) | Ember monthly (from 2018-01) | Ember (236.84 TWh 2025) |

Drivers: gas TTF and Henry Hub, coal, FX, carbon.

| Driver | Source | Licence status |
|---|---|---|
| Natural gas, Europe (TTF from 2015-04) | World Bank Pink Sheet, monthly, latest 2026M08 (IMF PCPS `PNGASEU` as cross-check) | **CC BY 4.0** confirmed on the Data Catalog record |
| Natural gas, US (Henry Hub) | EIA `natural-gas/pri/fut` `RNGWHHD`, daily to 2026-09-22 (key) | Public domain, attribute |
| Coal (Australian, South African) | World Bank Pink Sheet (Australia from 1970, South Africa from 1984) | CC BY 4.0 (third-party exception in the terms; none stated for these series) |
| EU carbon (EUA) | **No source.** EEX auction files download keyless but are not open-licensed; ICAP, Ember, Instrat, Sandbag unusable | Omitted and said so, unless Ziggy obtains permission from EEX |
| FX: USD, CNY, ZAR per EUR | ECB EXR, daily and monthly average, from 1999/2000 | ECB "free use", cite the ECB, state modifications |
| FX: RUB | Bank of Russia (`XML_daily`, `XML_dynamic`); ECB suspended RUB on 2022-03-01 | **Not open.** "Materials of the Website may only be used with the consent of the rightsholders", link mandatory |

## What verification changed (read first)

1. **The Wholesale index is EU-only unless a US source is cleared.** Every other region is "no market" or "no source". Publishing it as an "index" of four blocs would be untrue, so the site must label it as EU-only, or hold it back. STOP-1 decision.
2. **Retail is solid for EU and US, best-effort for China, blocked for Russia, tariff-derived for South Africa.** Russia's household price needs the Rosstat TLS decision, and China rests on two or three provinces.
3. **EU retail runs about nine months late** (latest 2025-S2 on 2026-09-29). HICP electricity (`prc_hicp_minr`, ECOICOP v2) starts only in 2020-01 in its current dataset; older data lives in frozen datasets `prc_hicp_midx` and `prc_hicp_manr`, which still answer with stale data ending 2025-12. Any nowcast needs a chain-link across that classification change.
4. **Ember's format changed in July 2026** (one row per area, month and source; `Area` = `EU` for the aggregate; True/False capitals). Ember's page dates are unreliable, so use file Last-Modified. Ember's monthly EU series starts 2016-01, so the SPEC's 2015-01 start holds for EU wholesale but not for EU mix.
5. **Licence corrections to the desk research:** Pink Sheet is CC BY 4.0 (confirmed). ECB has no "non-commercial" wording. CBR and Eskom are restrictive. GlobalPetrolPrices is CC BY-NC-ND (excluded).
6. **EIA's API returns intermittent HTTP 500s on valid requests** (about 5 of 18 calls); the adapter needs bounded retries. Row limit 5,000 per request, values are strings.
7. **Sums of Eurostat price components double-count** (`TAX_FEE_LEV_CHRG` includes VAT); adapters must not sum all codes.

## Hosts blocked or unreachable from this environment (owner action list)

`rosstat.gov.ru`, `gks.ru` (TLS: Russian national CA not in the trust store, not bypassed); `atsenergo.ru` (connection reset); `np-sr.ru` (502); `fedstat.ru` (403); `data.stats.gov.cn` (403); `cec.org.cn`; State Grid and China Southern Grid provincial sites (`*.sgcc.com.cn`, `gd.csg.cn`); NDRC price sub-site `jgs.ndrc.gov.cn`; provincial DRCs of Beijing, Sichuan, Jiangsu, Zhejiang, Shandong and Henan; `www.statssa.gov.za` (bot challenge); `dataservices.imf.org` (502); `carbonpricingdashboard.worldbank.org` (403); `www.eia.gov/opendata/bulk/` index page (403; the zips and `manifest.txt` work). None was worked around.

---

# Part A: EU (Eurostat)

All requests: base `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?...&format=JSON`. HTTP 200 on every request listed below. No host was blocked or unreachable (hosts used: ec.europa.eu only). Fixtures and MANIFEST.json (with exact URLs, UTC fetch times, sha256) are in `fixtures/eurostat/`, 5 files, 3.9-6.1 KB each. Nothing needed a key.

Terms used: "confirmed" = seen in a live response or page on 2026-09-29. Anything else is marked "not confirmed".

## Licence (applies to every entry below)

- Page: https://ec.europa.eu/eurostat/web/main/help/copyright-notice (fetched 2026-09-29, HTTP 200).
- Quoted reuse sentence: "Reuse of statistical data, metadata, publications, and other dissemination tools published on this website for commercial or non-commercial purposes is authorised provided the source is acknowledged."
- Conditions from the same page: modified data or text must be stated as modified, with a disclaimer of Eurostat's non-responsibility ("When reuse involves translations of publications or modifications to the data or text, this must be stated clearly to the end user of the information. A disclaimer regarding the non-responsibility of Eurostat shall be included."). Dataset citation form: "Source: [Eurostat dataset datacode link], [access date]" for customised versions; DOI form for the whole dataset (nrg_pc_204 DOI 10.2908/NRG_PC_204, seen in the response annotation).
- Exception (relevant if we ever show non-EU rows): "Data for countries other than: Member States of the European Union (EU) / Member States of the European Free Trade Association (EFTA) / official EU acceding and candidate countries" may not be reused commercially. The 204/205 country lists also include "United Kingdom" (metadata page, "Other countries"); we use EU27 and EU member states only, so no impact.
- Editorial content of the site is CC BY 4.0 (same page); the statistical data sentence above is the operative one.
- "Legal notice" / "no special procedure": "There is no special procedure or requirement for a written licence. Just download the material and use it, unless the material is listed in the exceptions above."

---

## E1. nrg_pc_204: electricity prices, household consumers, bi-annual

- Dataset/series code: `nrg_pc_204` (label "Electricity prices for household consumers - bi-annual data (from 2007 onwards)"). Series we want: freq=S, siec=E7000, nrg_cons=KWH2500-4999 (band DC), unit=KWH, currency=EUR, tax in {I_TAX, X_VAT, X_TAX}, geo=EU27_2020 and member states.
- Endpoint: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_204?geo=EU27_2020&geo=DE&currency=EUR&tax=I_TAX&nrg_cons=KWH2500-4999&sinceTimePeriod=2024-S1&format=JSON` (confirmed). Structure via SDMX 2.1 `.../sdmx/2.1/dataflow/ESTAT/nrg_pc_204/latest` also answers, HTTP 200, 5161 bytes (confirmed).
- Cadence: half-yearly. Reference period S1 = January-June, S2 = July-December (ESMS metadata: "the reference periods are from January to June for semester 1 and from July to December for semester 2"). Metadata page also says (item 10.1) "Electricity prices for the household sector are announced semestrially end-April and end-October for the previous reference period."
- Lag: latest period available today (2026-09-29) is 2025-S2 (OBS_PERIOD_OVERALL_LATEST = 2025-S2 in the response annotation; no 2026-S1 value for any geo tried). Dataset last updated 2026-09-24T23:00+0200 (this update ships `Info_note_NRG_20260917.pdf`, HTTP 200, 6 pages, content NOT read: no PDF text tool in this environment). Countries deliver "3 months after the reference period or earlier" (ESMS 14.1), but publication of 2025-S2 is still the newest 9 months after the period ends. Exact release-calendar dates: not confirmed (ESMS points to the Eurostat release calendar; not opened). The "end-April / end-October" wording in the ESMS does not match what we observe (S1 2026 absent at end of September); treat the ESMS wording as unreliable and plan for at least one semester of staleness.
- History start: EU27_2020 DC I_TAX first value 2007-S1, 38 semesters through 2025-S2 (counted). Dataset axis runs back to 1985-S1 for legacy pre-2007 bands (annotation OBS_PERIOD_OVERALL_OLDEST=1985-S1); ESMS 3.8: "The first full set of price data that was collected with the new methodology is available from the second semester 2007 onwards." (Note: our count shows values from 2007-S1 for EU27_2020 DC; ESMS says S2 2007 for the full set; use 2007-S1 as observed.)
- Units: EUR per kWh (also `PPS` and `NAC` (national currency) available in the currency dimension; the unit dimension is only `KWH`). ESMS 11.2: "Whenever prices are calculated and/or presented in Euro, the average exchange rates of the 2 quarters of the appropriate semester are taken as a reference" (so non-euro-country EUR series contain FX effects).
- Key needed: no.
- Licence: see top (Eurostat copyright notice).
- Tax codes (the whole tax code list of nrg_pc_204 and nrg_pc_205 is exactly these three, confirmed by an unfiltered-tax request on both): `X_TAX` = "Excluding taxes and levies" (ESMS: Level 1); `X_VAT` = "Excluding VAT and other recoverable taxes and levies" (Level 2); `I_TAX` = "All taxes and levies included" (Level 3). ESMS 3.4 text: "Level 1 prices: prices excluding taxes and levies. Level 2 prices: prices excluding VAT and other recoverable taxes and levies. Level 3 prices: prices including all taxes and levies." There is no `X_TAX_X_VAT` code. For "excluding VAT and recoverable levies" use `X_VAT`.
- Bands (confirmed in response labels): DA KWH_LT1000, DB KWH1000-2499, DC KWH2500-4999, DD KWH5000-14999, DE KWH_GE15000, plus TOT_KWH.
- Known breaking changes: none found for the code or dimensions. Data flags: provisional data marked "p" per the ESMS (no flags present in our fixture rows). ESMS 17.2: "Time series breaks caused by major revisions are flagged"; values can be revised. Since reference period 2021 S2 countries report subsidies/allowances, which can make X_TAX exceed I_TAX (seen: NL 2025-S2 X_TAX 0.2692 > I_TAX 0.2558 > X_VAT 0.2114).
- Date checked: 2026-09-29.
- Latest values seen (EUR/kWh, band DC, 2025-S2):

| geo | I_TAX | X_VAT | X_TAX |
|---|---|---|---|
| EU27_2020 | 0.2896 | 0.2456 | 0.2059 |
| DE | 0.3869 | 0.3252 | 0.2625 |
| FR | 0.2561 | 0.2158 | 0.1785 |
| IT | 0.2966 | 0.2693 | 0.2190 |
| ES | 0.2669 | 0.2223 | 0.1840 |
| PL | 0.2709 | 0.2202 | 0.1539 |
| NL | 0.2558 | 0.2114 | 0.2692 |

  EU27_2020 I_TAX: 2024-S2 0.2887, 2025-S1 0.2879, 2025-S2 0.2896. DE I_TAX: 2024-S2 0.3943, 2025-S1 0.3835, 2025-S2 0.3869. (Matches the desk-research figures.)

## E2. nrg_pc_205: electricity prices, non-household consumers, bi-annual

- Dataset/series code: `nrg_pc_205` (response label reads "Electricity prices for industrial consumers - bi-annual data (from 2007 onwards)"; the ESMS calls the sector "final non-household"). Series: freq=S, siec=E7000, nrg_cons=MWH2000-19999 (band ID), unit=KWH, currency=EUR, tax in {I_TAX, X_VAT, X_TAX}.
- Endpoint: `.../data/nrg_pc_205?geo=EU27_2020&geo=DE&...&currency=EUR&nrg_cons=MWH2000-19999&sinceTimePeriod=2024-S1&format=JSON` (confirmed).
- Cadence, lag, history: same as E1. Latest 2025-S2, updated 2026-09-24T23:00+0200; EU27_2020 X_VAT first value 2007-S1, 38 semesters; axis back to 1985-S1.
- Units: EUR/kWh (unit dimension KWH, price per kWh even though the band is in MWh). Currency dimension: EUR, PPS, NAC.
- Key needed: no. Licence: see top.
- Bands (confirmed): IA MWH_LT20, IB MWH20-499, IC MWH500-1999, ID MWH2000-19999, IE MWH20000-69999, IF MWH70000-149999, IG MWH_GE150000, TOT_KWH, plus pre-2007 legacy codes (MWH30, MWH50, MWH160, MWH1250, MWH2000, MWH10000, MWH24000, MWH50000, MWH70000) that live in the same dataset with the same dimension (a filter on nrg_cons is mandatory).
- Which tax code approximates "excluding VAT and recoverable levies": `X_VAT` (label "Excluding VAT and other recoverable taxes and levies", ESMS Level 2). This is the level closest to what a business actually bears; `X_TAX` strips all taxes and levies (Level 1), `I_TAX` includes everything (Level 3).
- Known breaking changes: none found. Same provisional flag and revision policy as E1.
- Date checked: 2026-09-29.
- Latest values seen (EUR/kWh, band ID, 2025-S2):

| geo | I_TAX | X_VAT | X_TAX |
|---|---|---|---|
| EU27_2020 | 0.1920 | 0.1596 | 0.1349 |
| DE | 0.2369 | 0.1922 | 0.1613 |
| FR | 0.1425 | 0.1212 | 0.1068 |
| IT | 0.2177 | 0.1948 | 0.1587 |
| ES | 0.1431 | 0.1191 | 0.1061 |
| PL | 0.2135 | 0.1735 | 0.1127 |
| NL | 0.2192 | 0.1811 | 0.1425 |

## E3. nrg_pc_204_c (and nrg_pc_205_c): price components, annual

- Dataset/series code: `nrg_pc_204_c` ("Electricity prices components for household consumers - annual data (from 2007 onwards)"); `nrg_pc_205_c` ("... non-household consumers - annual data (from 2007 onwards)") also exists (DE, band ID, NRG_SUP returned 0.1052; not saved as a fixture). Dimensions: freq=A, nrg_cons, nrg_prc (component), currency, geo, time.
- Endpoint: `.../data/nrg_pc_204_c?geo=DE&currency=EUR&nrg_cons=KWH2500-4999&sinceTimePeriod=2024&format=JSON` (confirmed).
- Cadence: annual (ESMS: "Annual prices ... are reported once a year together with the data for the second semester"). Lag: latest 2025; dataset updated 2026-08-12T11:00+0200 (nrg_pc_205_c 2026-08-11). History start: 2017 (first value with the geo/band above; the dataset title says "from 2007 onwards"; only 9 years 2017-2025 returned, so pre-2017 is not confirmed).
- Units: EUR/kWh. Key: no. Licence: see top.
- Component codes (confirmed, 15): NRG_SUP energy and supply; NETC network costs; TAX_FEE_LEV_CHRG taxes, fees, levies and charges; VAT; TAX_RNW; TAX_CAP; TAX_ENV; TAX_NUC; *_ALLOW allowance variants (TAX_FEE_LEV_CHRG_ALLOW, TAX_RNW_ALLOW, TAX_CAP_ALLOW, TAX_ENV_ALLOW, TAX_NUC_ALLOW, ALLOW_OTH); OTH other.
- DE DC 2025 (EUR/kWh): NRG_SUP 0.1481, NETC 0.1130, TAX_FEE_LEV_CHRG 0.1241, VAT 0.0615, TAX_RNW 0.0028, TAX_CAP 0.0237, TAX_ENV 0.0205, TAX_NUC 0.0, OTH 0.0156, all allowances 0.0. Arithmetic check I did (derived, not stated by Eurostat): NRG_SUP + NETC + TAX_FEE_LEV_CHRG = 0.3852, equal to the mean of DE 2025-S1 and 2025-S2 I_TAX (0.3835, 0.3869); and TAX_RNW + TAX_CAP + TAX_ENV + TAX_NUC + OTH + VAT = 0.1241 = TAX_FEE_LEV_CHRG. So TAX_FEE_LEV_CHRG includes VAT and is a subtotal; adapters must not sum all codes.
- Sibling datasets seen: `nrg_pc_204_h` = "Electricity prices for domestic consumers - bi-annual data (until 2007)", uses the OLD dimension name `consom` (updated 2024-01-03; not used). `nrg_pc_204_v` = "Household consumption volumes of electricity by consumption bands" (dimensions freq, nrg_cons, siec, unit, geo, time; updated 2026-08-12; not fetched further; possibly useful for band weights, not confirmed).
- Known breaking changes: none found. Date checked: 2026-09-29.

## E4. prc_hicp_minr: HICP electricity, monthly (ECOICOP ver. 2)

- Dataset/series code: `prc_hicp_minr`, label "Harmonised index of consumer prices (HICP) - ECOICOP ver.2 - indices and rates of change, monthly data"; item `coicop18=CP0451` label "Electricity (ND)"; units `I25` (Index, 2025=100), `I15` (2015=100), `RCH_A` (annual rate of change, %), also RCH_M and RCH_MV12MAVR per desk research (only I25, RCH_A, I15 confirmed live here). Dimensions: freq=M, unit, coicop18, geo, time.
- Endpoint: `.../data/prc_hicp_minr?geo=EU&geo=EA&geo=DE&geo=FR&coicop18=CP0451&unit=I25&unit=RCH_A&sinceTimePeriod=2025-09&format=JSON` (confirmed).
- Cadence: monthly. Lag: latest 2026-08, dataset updated 2026-09-17T11:00+0200 (about 2.5 weeks after month end). ESMS: "flash estimate ... usually disseminated on the last working day of the reference month or shortly thereafter" (for headline and selected components; whether CP0451 has a flash: not confirmed). Release calendar: "Euro indicators release schedule" page, not opened.
- History start in THIS dataset (EU geo, CP0451): I25 from 2020-01, I15 from 2019-12, RCH_A from 2021-01 (counted from live responses). Older history lives in frozen COICOP datasets: `prc_hicp_midx` ("HICP - monthly data (index) (1996-2025)", updated 2026-02-06, dimension `coicop`, EU CP0451 I15 2025-12 = 160.6, 2025-11 = 160.31) and `prc_hicp_manr` ("(1997-2025)", RCH_A EU CP0451 2025-12 = 0.8, 2025-11 = 0.9). Both stop at 2025-12 and still answer HTTP 200 with stale data (the silent-stale-data trap is real for midx/manr). Chain-linking old and new series across the classification change: not tested.
- Difference from desk research: the desk note listed `prc_hicp_minr` among the old datasets that stopped at 2025-12. Live check: `prc_hicp_minr` is the new ECOICOP v2 dataset; sending the old `coicop=CP0451` dimension to it returns HTTP 400 "INVALID_QUERY_DIMENSION ... Dimension "COICOP" is not defined", so it fails loudly. midx and manr are the ones that go stale silently.
- Units: index points (2025=100) or percent. Not per kWh. Key: no. Licence: see top.
- Known breaking change (confirmed, ESMS text): "As established in EU regulation 2024/3159, starting with the publication of the January 2026 data, a revised classification (ECOICOP version 2) ... is applied for the full series." "The data using the ECOICOP classification (1996-2025) is available in dissemination in Eurostat database and frozen unless error corrections are needed. Data starting from January 2026 are only available under the ECOICOP version 2 classification. Back series recalculated in ECOICOP version 2 are also provided." Base year moved to 2025=100.
- Date checked: 2026-09-29.
- Latest values seen (2026-08): I25 EU 102.58, EA 102.08, DE 94.5, FR 99.63; RCH_A EU 2.3, EA 2.8, DE -5.6, FR 1.1. (2025-09: I25 EU 100.08, RCH_A EU 1.9.)

## E5. Electricity consumption for basket weights (Eurostat, EU-27)

- Dataset/series code: `nrg_cb_e` ("Supply, transformation and consumption of electricity", annual); dimensions freq=A, nrg_bal, siec=E7000, unit=GWH, geo, time. Balance items: `FC` "Final consumption" and `ID` "Inland demand" (also AFC, LOSS, DL, IMP, EXP, and about 60 sector items).
- Endpoint: `.../data/nrg_cb_e?geo=EU27_2020&nrg_bal=FC&nrg_bal=ID&siec=E7000&unit=GWH&sinceTimePeriod=2022&format=JSON` (confirmed).
- Cadence: annual. Lag: 2025 already published, dataset updated 2026-09-11T11:00+0200; the 2025 values carry status flag `p` (provisional) for every geo. ESMS 14.1 says dissemination is due 13 months after year end by regulation (Regulation (EC) 1099/2008), first revision about 12 months after year end, cycle completed about 16 months after; observed publication is earlier than that, so expect 2025 revisions. History start: 1990 (EU27_2020, 36 years).
- Units: GWH (gigawatt-hour), confirmed in the unit dimension. 1 TWh = 1,000 GWh.
- Values (GWh, 2025, provisional): EU27_2020 FC 2,412,055.15 (2,457,651.2 in 2024); EU27_2020 ID 2,664,060.8; DE FC 473,562 / ID 500,864; FR FC 423,523; IT FC 293,080; ES FC 245,441; PL FC 152,808; NL FC 110,386. FC excludes network losses and energy-sector own use; ID (inland demand) is the closer analogue of a "demand" figure that includes losses. Which of FC or ID matches Ember's "Demand" definition: not confirmed here (Ember is covered by another agent).
- Monthly sibling `nrg_cb_em` ("Supply, transformation and consumption of electricity - monthly data", updated 2026-09-28T23:00+0200): balance items only IMP, IMP_FROM_EU, EXP, EXP_TO_EU, TI_EHG_EPS, DL, AIM ("Available to internal market"). It has NO `FC`. AIM EU27_2020 latest value 2026-06 = 197,223.841 GWh (2026-07 and 2026-08 exist on the time axis but return no value). Difference from desk research: the desk note said `nrg_cb_em` had 2026-08 available; that is only the time axis, the latest actual value is 2026-06. The dataset ID nrg_cb_e / nrg_cb_em, not nrg_bal_c, is the right code (nrg_bal_c not tested; not needed).
- Key: no. Licence: see top. Known breaking changes: none found; ESMS notes zeros can mean unavailable, confidential, real zero or negligible ("cannot distinguish"), and reporting since 2017 allows 3 decimals. Date checked: 2026-09-29.
- Scope note for non-EU regions: Eurostat gives EU-27 only (plus EFTA and candidates). Copyright page says data for countries such as the United States, Japan or China may not be reused commercially. US, China, Russia and South Africa weights should therefore come from Ember (CC BY 4.0 per SOURCES.md, verified by another agent) rather than from Eurostat.

## Adapter parse notes (JSON-stat 2.0)

- Response top-level keys: `version` "2.0", `class` "dataset", `label`, `source` "ESTAT", `updated`, `value`, `status` (only when flagged, e.g. nrg_cb_e; absent in the 204/205/204_c/HICP fixtures), `id`, `size`, `dimension`, `extension`.
- `id` is the ordered list of dimensions; `size` is the length of each, same order; `dimension[<id>].category.index` maps code to position (an object here, not an array).
  - nrg_pc_204 / nrg_pc_205: id = [freq, siec, nrg_cons, unit, tax, currency, geo, time].
  - nrg_pc_204_c: [freq, nrg_cons, nrg_prc, currency, geo, time].
  - prc_hicp_minr: [freq, unit, coicop18, geo, time].
  - nrg_cb_e: [freq, nrg_bal, siec, unit, geo, time].
- `value` is an OBJECT keyed by the flat row-major index as a string, NOT an array, and missing observations are simply absent (sparse): flat = sum(pos_i * stride_i) with the last dimension (time) varying fastest. Worked example, household fixture size [1,1,1,1,3,1,7,4]: DE I_TAX 2025-S2 is tax=2, geo=1, time=3 so key 2*28 + 1*4 + 3 = "63", value 0.3869 (verified).
- Position order in `category.index` is NOT the request order: in the nrg_pc fixtures it came back EU27_2020, DE, ES, FR, IT, NL, PL (EU first, then alphabetical); in nrg_cb_e the same; in prc_hicp_minr EU, EA, DE, FR (request order there). Always decode with the `index` map, never assume request order (confirms the desk-research warning).
- `status` (flags) uses the same flat keys, e.g. `{"7": "p"}`; `p` = provisional.
- Time labels: semester "2025-S2", month "2026-08", year "2025". `label` of nrg_pc_205 says "industrial consumers".
- Query parameters used and confirmed to work: repeated `geo=`, `sinceTimePeriod=`, `lastTimePeriod=`, `untilTimePeriod` not tried. Error responses are HTTP 400 with body `{"error":[{"status":400,"id":150,"label":"INVALID_QUERY_DIMENSION..."}]}` (seen).
- Response headers of a data request include `Access-Control-Allow-Origin: *`. Rate limits: not confirmed (none observed at about 40 requests in this session; Eurostat's API guidance page was not opened).
- Cache-friendly: one request per dataset per run is enough (fixtures are 4-6 KB; a full unfiltered nrg_pc_205 request for one geo, all bands and taxes, was 207 KB).

## Differences from the desk research (SOURCES.md items 1, 2, 12)

1. Tax codes: the desk note "X_TAX, X_VAT exist ... only confirmed I_TAX" is now confirmed: exactly three codes X_TAX / X_VAT / I_TAX; X_VAT is the "excluding VAT and recoverable levies" level.
2. prc_hicp_minr: it is the NEW ECOICOP v2 dataset (dimension coicop18), it errors (HTTP 400) on the old `coicop` dimension; the stale-data-silently trap applies to `prc_hicp_midx` and `prc_hicp_manr`, not to minr. Its own history is short: I25 EU CP0451 from 2020-01, RCH_A from 2021-01.
3. Monthly consumption: `nrg_cb_em` has no FC and its latest AIM value is 2026-06, not 2026-08.
4. Desk claim "history 2007 onwards, axis to 1985" is confirmed (first value 2007-S1 for the EU27 DC/ID series).
5. Confirmed unchanged: EU27_2020 DC 2025-S1 0.2879, S2 0.2896; DE S2 0.3869; nrg_cb_e EU27_2020 2025 FC 2,412,055 GWh (2,412,055.15); dataset update dates 2026-09-24 (204/205), 2026-08-12 (204_c), 2026-09-17 (HICP), 2026-09-11 (nrg_cb_e).
6. Not confirmed: the release calendar dates for the next 204/205 release (S1 2026); the content of Info_note_NRG_20260917.pdf; HICP CP0451 flash availability; rate limits; whether Ember "Demand" is comparable to FC or ID.

---

# Part B: US (EIA) and Ember

Method: live requests through the session proxy (TLS verified). EIA API calls used the key from the environment only; every recorded URL has `api_key=REDACTED`; EIA responses do not echo the key (verified). Fixtures: `fixtures/eia/` and `fixtures/ember/`, each with `MANIFEST.json` (url, fetched_at, sha256, trimming note, source_kind=live). "Latest period" is what the live source returned on 2026-09-29 around 19:00 UTC. Anything not verified is marked "not confirmed".

## Differences from the desk research (SOURCES.md) in one place
1. EIA-930 fuel-type history in the API starts 2019-01-01, not 2015 (route metadata `startPeriod`; first row `2019-01-01T00`, US48). The 2015 in the desk note is not supported by the API. Whether the bulk EBA.zip reaches back to 2015 is not confirmed (zip not downloaded).
2. EIA retail-sales API returns exactly the desk figures for 2026-07 (RES 18.31, COM 14.53, IND 9.77, ALL 14.99 c/kWh) — confirmed via the API, not via EPM Table 5.6.A. Whether the latest month is a "preliminary estimate" is NOT visible in the API (no flag column); not confirmed here.
3. Bulk directory page `https://www.eia.gov/opendata/bulk/` returned HTTP 403 ("You do not have permission to view this directory or page.", HTTP 503 AkamaiGHost on HEAD), but `manifest.txt` and the three zips (ELEC, EBA, NG) answer 200 on HEAD and on a 4-byte Range GET. Sizes and dates match the desk note except ELEC.zip Last-Modified is Fri 25 Sep 2026 10:09 GMT (manifest `modified` 2026-09-23T17:01:12-04:00; the desk said updated 2026-09-23).
4. Ember "EU" aggregate: the Area is named exactly `EU` (Area type `Region`, blank ISO 3), not "European Union". Its monthly history starts 2016-01 (EU member countries start 2015-01). The desk note said only "present".
5. Ember US monthly is confirmed 2001-01 to 2026-08 (desk: latest month not confirmed).
6. Ember monthly file: sampled area names give at least 98 areas (sampling every 100 KB; may miss small blocks); the Ember page says 88. Not reconciled.
7. Ember price page says "Updated monthly" and its own "Last Updated" text reads 16/01/2026, but the files are stamped 2026-09-29 and contain 2026-09 (partial) monthly and daily data to 2026-09-28. Page dates are unreliable; use file Last-Modified/ETag.
8. Ember monthly page says data sources are "EIA, Eurostat, Energy Institute" while the yearly page says "EIA, Eurostat, BP, UN". Not reconciled.
9. Ember licence: the desk note quoted a sentence; verified verbatim (below). Attribution wording: Ember asks only "as long as you credit us"; no fixed citation string found.

---------------------------------------------------------------------
## EIA-1. US retail sales of electricity: price by sector, and sales quantity (basket weights)
- code/route: `electricity/retail-sales`; data columns `price` (cents per kilowatt-hour), `sales` (million kilowatt hours), also `revenue`, `customers`; facets `stateid` (US, 50 states + DC, census divisions), `sectorid` (RES, COM, IND, TRA, OTH, ALL).
- endpoint: `https://api.eia.gov/v2/electricity/retail-sales/data/?api_key=KEY&frequency=monthly&data[0]=price&data[1]=sales&facets[stateid][]=US&facets[sectorid][]=RES&facets[sectorid][]=COM&facets[sectorid][]=IND&facets[sectorid][]=ALL&start=2025-01&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000` (use `curl -g` because of brackets). Route metadata: `https://api.eia.gov/v2/electricity/retail-sales?api_key=KEY`.
- cadence: monthly, quarterly and annual (metadata `frequency` ids `monthly` `quarterly` `annual`).
- lag (latest period today): monthly 2026-07 (about 2 months); annual 2025 (already published). Metadata `endPeriod` = 2026-07.
- history start: 2001-01 monthly (metadata `startPeriod` 2001-01; first row 2001-01 ALL = 6.75 c/kWh; 307 monthly rows per US/sector series).
- units: price cents per kilowatt-hour; sales million kilowatt hours (= GWh). Values are JSON strings, not numbers. Latest 2026-07 US: RES 18.31, COM 14.53, IND 9.77, ALL 14.99 c/kWh; sales ALL 415,276 million kWh. Annual 2025 sales (million kWh): ALL 4,058,007; RES 1,514,993; COM 1,493,486; IND 1,042,217; TRA 7,311; OTH 0. Annual 2025 price ALL 13.63, RES 17.3, COM 13.41, IND 8.62 c/kWh. (Ember's US 2025 Demand row is 4,532 TWh: different concept, includes losses/own use; do not mix.)
- key needed: yes (`api_key`; without it `API_KEY_MISSING` per desk note; not re-tested here). Keyless fallback: bulk `ELEC.zip` (see EIA-6).
- licence: "U.S. government publications are in the public domain and are not subject to copyright protection." (https://www.eia.gov/about/copyrights_reuse.php) plus the same page: "you should use an acknowledgment, which includes the publication date, such as: \"Source: U.S. Energy Information Administration (Oct 2008).\"" API terms (https://www.eia.gov/opendata/terms-of-service.php): "You should use the \"EIA\" or the \"U.S. Energy Information Administration\" names in order to identify the source of API content"; "You may not modify or falsely represent content accessed through the API and still claim the source is the EIA."; the EIA logo may not be used without written permission.
- known breaking changes / quirks: (a) row limit 5,000 per request: `length=6000` returns 5,000 with warning "parameter out of range: length"; paginate with `offset` (offset=5000 confirmed to return the next 5,000 of total=114,204 rows for all states/sectors). (b) A warning "incomplete return" appears on many responses even when the whole result is returned or a small `length` was asked; do not treat any warning as an error. (c) The API intermittently returned HTTP 500 with body "Something unexpected happened." on valid requests (about 5 of 18 calls in this session; the same URL succeeded on retry): the adapter needs bounded retries with backoff. (d) Response shape: `{"response":{"total":"307","dateFormat":"YYYY-MM","frequency":"monthly","data":[...],"description":...},"request":{...},"apiVersion":"2.1.14"}`; `total` is a string. (e) `period` is `YYYY-MM` monthly, `YYYY` annual, `YYYY-"Q"Q` quarterly. (f) The `request` echo does not include the key. (g) Sector `OTH` and `TRA` exist; ALL is the all-sector average (whether ALL equals a sales-weighted sum of RES+COM+IND+TRA was not checked). (h) Numeric throttle limits are not stated on the documentation page ("your API key will be automatically but temporarily suspended"); no X-RateLimit headers were seen. Rate limit: not confirmed.
- state level: exists (stateid). Example fixture TX and CA ALL 2026-07: 10.91 and 30.71 c/kWh.
- date checked: 2026-09-29. Fixtures: `retail_sales_*.json`.

## EIA-2. US monthly generation by fuel (national)
- code/route: `electricity/electric-power-operational-data`, data column `generation` ("Utility Scale Electricity Net Generation"); facets `location` (US = "U.S. Total"), `sectorid` (99 = All Sectors), `fueltypeid` (ALL, NG, COL, NUC, WND, SUN, HYC, PET, OTH, GEO, BIO, HPS, AOR, REN, FOS ...; full list in `operational_data_facet_fueltypeid.json`).
- endpoint: `https://api.eia.gov/v2/electricity/electric-power-operational-data/data/?api_key=KEY&frequency=monthly&data[0]=generation&facets[location][]=US&facets[sectorid][]=99&facets[fueltypeid][]=ALL&facets[fueltypeid][]=NG&...&start=2026-05&length=5000`
- cadence: monthly, quarterly, annual.
- lag (latest period today): 2026-07 (metadata `endPeriod` 2026-07).
- history start: 2001-01 (first row ALL = 332,493.16 thousand MWh; 307 monthly periods).
- units: thousand megawatthours (= GWh). 2026-07 US all fuels 453,744; NG 205,294; COL 75,062; NUC 71,172; SUN 41,412; WND 32,184; HYC 20,266; AOR 78,945; HPS -524 (pumped storage net can be negative). Sample check against Ember for the same month: Ember US 2026-07 Total generation 467.9 TWh vs EIA 453.7 TWh; Ember solar 52.8 vs EIA SUN 41.4 TWh. EIA `SUN` is utility-scale; Ember includes an estimate of small-scale solar (EIA also has `TSN`/`TPV`/`DPV` "estimated total/small scale" codes; not fetched). Choose one source per series and do not mix.
- key needed: yes. Keyless fallback: `ELEC.zip`.
- licence: as EIA-1.
- known breaking changes / quirks: fuel codes are EIA's (NG, COL, WND, SUN, HYC, NUC, PET, OTH ...), not the RTO codes; `sectorid` values are strings ("99"). Same 5,000-row/500/warning behaviour as EIA-1.
- date checked: 2026-09-29. Fixtures: `operational_data_*.json`.

## EIA-3. US grid operating data (EIA-930), hourly and daily generation by fuel
- code/route: `electricity/rto/fuel-type-data` (hourly) and `electricity/rto/daily-fuel-type-data` (daily); facets `respondent` (US48 = "United States Lower 48"), `fueltype` (COL, NG, NUC, OIL, OTH, SUN, WAT (hydro), WND, GEO, BAT, PS, OES, UNK ...), `timezone` (daily only). Other rto routes: region-data, region-sub-ba-data, interchange-data, daily-region-data, daily-region-sub-ba-data, daily-interchange-data. There is NO price route under rto.
- endpoint: `https://api.eia.gov/v2/electricity/rto/daily-fuel-type-data/data/?api_key=KEY&frequency=daily&data[0]=value&facets[respondent][]=US48&facets[timezone][]=Eastern&start=2026-09-25&length=5000`; hourly: `.../rto/fuel-type-data/data/?...&frequency=hourly&facets[respondent][]=US48&start=2026-09-29T00`.
- cadence: hourly (UTC and local-hourly) and daily.
- lag (latest period today): daily US48 latest 2026-09-28 (metadata endPeriod 2026-09-28); hourly US48 latest row returned 2026-09-29T03 (UTC) at ~19:10 UTC, metadata endPeriod 2026-09-29T06 (other respondents) — about half a day. Bulk EBA.zip is "Older Than 7 Days" per its manifest title.
- history start: 2019-01-01 (metadata startPeriod 2019-01-01 for both routes; first US48 rows 2019-01-01T00). NOT 2015. US48 hourly total rows 664,655.
- units: `value` megawatthours (hourly = MWh per hour). US48 2026-09-28 daily NG 4,990,171 MWh; COL 1,910,252; NUC 2,134,167.
- key needed: yes.
- licence: as EIA-1.
- known breaking changes / quirks: `period` formats `YYYY-MM-DD"T"HH24` (hourly, UTC, no zone suffix) and `YYYY-MM-DD` (daily); daily has one series per `timezone` facet (Eastern, Pacific ...), so filter it or double count. Fuel categories include storage (BAT, PS, OES) that can be negative/positive; self-reported and revisable (revision behaviour not confirmed here). Monthly national mix is better served by EIA-2 or Ember.
- date checked: 2026-09-29. Fixtures: `rto_*.json`.

## EIA-4. Henry Hub natural gas spot price
- code/route: `natural-gas/pri/fut`, facet `series` = `RNGWHHD` ("Henry Hub Natural Gas Spot Price (Dollars per Million Btu)"; also RNGC1-RNGC4 futures contracts 1 to 4). The route holds `duoarea`=RGC, `product`=EPG0, `process`=PS0 for spot.
- endpoint: `https://api.eia.gov/v2/natural-gas/pri/fut/data/?api_key=KEY&frequency=daily&data[0]=value&facets[series][]=RNGWHHD&start=2026-09-01&length=5000` (frequency `daily`, `weekly`, `monthly`, `annual` all exist).
- cadence: daily, weekly, monthly, annual.
- lag (latest period today): daily RNGWHHD latest 2026-09-22; monthly latest 2026-08 (2.78 $/MMBtu; September not yet published). Route metadata `endPeriod` 2026-09-18 is for the default weekly frequency and is not the daily end. Consistent with the desk note that the page release is weekly (release date 9/23/2026).
- history start: daily 1997-01-07 (3.82), 7,466 daily rows; monthly 1997-01 (3.45), 356 monthly rows. (The route's `startPeriod` 1993-12-24 belongs to the futures series.)
- units: $/MMBTU (field `units` = "$/MMBTU"; `value` string). Confirmed the January 2026 spike: 2026-01-23 = 30.72, 2026-01-26 = 25.01, 2026-01-27 = 17.19; late September 2026 = 2.90-2.97.
- key needed: yes. Keyless fallback: `NG.zip` (4,425,090 bytes).
- licence: as EIA-1. The futures series RNGC1-4 (NYMEX) are not used; whether their redistribution has extra terms was not checked (not confirmed).
- known breaking changes / quirks: spot dates are business days only; same limits as EIA-1.
- date checked: 2026-09-29. Fixtures: `henry_hub_*.json`, `natural_gas_pri_fut_*.json`.

## EIA-5. US wholesale / hub electricity prices (EIA "Wholesale Electricity and Natural Gas Market Data")
- code/route: none in the API. The API `electricity` routes are retail-sales, electric-power-operational-data, rto, state-electricity-profiles, operating-generator-capacity, facility-fuel (verified); the rto routes carry no prices.
- endpoint: page `https://www.eia.gov/electricity/wholesale/`; files `https://www.eia.gov/electricity/wholesale/xls/ice_electric-2026.xlsx` (71,441 bytes, Last-Modified Wed 16 Sep 2026 18:17:10 GMT), archives `xls/archive/ice_electric-YYYYfinal.xlsx` (2017-2025), `.xls` 2014-2016, and `ice_electric-historical.zip` (2001 to 2013). Not downloaded.
- cadence: "updated biweekly" (page). Daily price rows.
- lag (latest period today): not confirmed (2026 file last modified 2026-09-16).
- history start: per hub (page): Mid-C, PJM West, SP15-1, Palo Verde, Mass Hub 2001; Indiana Hub 2006; SP15-2 and NP15 2009; ERCOT North 2014.
- units: not read from a file (columns per page: high price, low price, weighted-average price, volume, number of trades, counterparties); the price unit is not confirmed here.
- key needed: no (static files).
- licence: NOT free to redistribute on the evidence. Quote: "The market data provided here are republished, with permission, from data collected by the Intercontinental Exchange (ICE) and are updated biweekly." and "If a certain hub or time period does not appear, EIA does not have access to it through the above-mentioned agreement. The data and methodology would have to be obtained directly from ICE." (https://www.eia.gov/electricity/wholesale/). The general EIA policy says "U.S. government publications are in the public domain..." but also "You may see on our website documents, illustrations, photographs, or other information resources contributed or licensed by private individuals, companies, or organizations that may be protected by U.S. and foreign copyright laws." (https://www.eia.gov/about/copyrights_reuse.php). No sentence on that page states these ICE-derived prices are public domain or free to reuse. Verdict: not confirmed reusable; do not publish; ask EIA (the page offers "Contact data experts").
- known breaking changes: page is Excel by year, ICE product names differ by hub (e.g. PJM WH Real Time Peak vs NP15 EZ Gen DA LMP), i.e. the hubs are peak products of different market types, not a single day-ahead price. US has no single national day-ahead price.
- date checked: 2026-09-29. No fixture (nothing fetched beyond the page and a HEAD).

## EIA-6. EIA keyless bulk download
- code/route: manifest `https://www.eia.gov/opendata/bulk/manifest.txt` (200, text/plain, 28,398 bytes); datasets `ELEC`, `EBA`, `NG`, plus AEO, COAL, EMISS, IEO, INTL, NUC_STATUS, PET, PET_IMPORTS, SEDS, STEO, TOTAL.
- endpoint/size today (HEAD): `https://www.eia.gov/opendata/bulk/ELEC.zip` 293,234,846 bytes, Last-Modified Fri 25 Sep 2026 10:09:38 GMT (manifest modified 2026-09-23T17:01:12-04:00); `EBA.zip` 692,669,101 bytes, Tue 29 Sep 2026 09:51:54 GMT (manifest 2026-09-29T05:04:05-04:00); `NG.zip` 4,425,090 bytes, Fri 25 Sep 2026 10:09:57 GMT (manifest 2026-09-24T15:54:15-04:00). All three reachable from this environment (HEAD 200; Range GET returns bytes). The bulk index page itself `https://www.eia.gov/opendata/bulk/` returned 403 (GET) / 503 AkamaiGHost (HEAD) — do not depend on it, use manifest.txt.
- cadence: the desk note says twice daily at 5 a.m. and 3 p.m. Eastern (from an EIA page); not re-verified here (manifest timestamps are consistent with a daily update at about that time).
- key needed: no.
- licence: as EIA-1; manifest `accessLevel` "public", `accessLevelComment` "series copyright field contains further information" (series-level copyright field inside the files not inspected: not confirmed).
- units/format: JSON download file (line-per-series, legacy series ids); format per manifest "XML and JSON data API, JSON download file". Not opened.
- known breaking changes: manifest lists legacy dataset ids (ELEC, EBA, NG); the mapping from bulk series ids to API v2 routes was not checked.
- date checked: 2026-09-29. Fixture: `bulk_manifest_trimmed.json` (ELEC, EBA, NG entries only).

---------------------------------------------------------------------
## EMBER-1. Monthly electricity generation, demand, emissions and carbon intensity
- code/route: dataset "Monthly Electricity Data" (page https://ember-energy.org/data/monthly-electricity-data/). Global file `https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv`; Europe-only `.../release_generation_monthly_lower.csv`.
- endpoint: the two URLs above, plain GET (accept-ranges: bytes), keyless.
- cadence: "The data is updated twice a month with an update in the first week of the month followed by a second update in the third week of the month." (page). Global file Last-Modified Fri 18 Sep 2026 21:29:31 GMT, ETag `1932fe694a4679159e119c2f6b9255e5`, 28,333,064 bytes; Europe file 14,423,164 bytes, 18 Sep 2026 21:29:24 GMT.
- lag (latest period today), per area, measured from the file: EU 2026-08; China 2026-08; United States 2026-08; Russia 2026-07; South Africa 2026-07.
- history start (measured from the file): United States 2001-01; China 2016-01; EU 2016-01; Russia 2019-01; South Africa 2018-01. Months present: China 128, EU 128, Russia 91, South Africa 103, US 308 (no gaps checked beyond count consistency with start/end).
- units: Generation and Demand in TWh per month (column `Generation (TWh)`, the Demand and Net imports rows use the same column); `Emissions (MtCO2e)`; shares in %; `Emissions intensity (gCO2e/kWh)`. Carbon intensity = the `Emissions intensity (gCO2e/kWh)` value on the `Total generation` row (per source on the other rows; blank for Demand). 2026 latest values: EU 2026-08 total generation 214.481 TWh, intensity 215.991; China 2026-08 1,021.987 TWh, 550.104; US 2026-08 465.153 TWh, 402.872; Russia 2026-07 84.947 TWh, 362.285; South Africa 2026-07 19.41 TWh, 735.549.
- exact header (23 columns, monthly and Europe file): `Area,ISO 3 code,Date,Area type,Electricity source,Is aggregated source,Generation (TWh),Generation YoY change (TWh),Generation YoY change (%),Share of generation (%),Share of generation YoY change (% points),Emissions (MtCO2e),Emissions YoY change (MtCO2e),Emissions YoY change (%),Share of emissions (%),Emissions intensity (gCO2e/kWh),Continent,Ember region,EU member,OECD member,G20 member,G7 member,ASEAN member`. Date is `YYYY-MM-01`. Booleans are `True`/`False` (Python-style capitals, not TRUE/FALSE as the page text says).
- labels: EU aggregate is `Area` = `EU`, `Area type` = `Region`, `ISO 3 code` blank, `Continent`/`Ember region` blank, `EU member` = False on that row (the flags describe the row, not a membership). Countries: `Area type` = `Country or economy`; ISO 3 codes CHN, RUS, ZAF, USA; area names "China", "Russia", "South Africa", "United States". Other names seen: "Türkiye", "Taiwan (China)", "The Philippines", "Bosnia Herzegovina", "Viet Nam", "Czechia". Regions include ASEAN, Asia, EU, Europe, G20, G7, Latin America and Caribbean, North America, OECD, Oceania, World. The file is sorted by Area (case-sensitive, so "EU" sorts before "Ecuador") then by date.
- `Electricity source` values seen for the five areas: Bioenergy, Clean, Coal, Demand, Fossil, Gas, Hydro, Hydro, bioenergy and other renewables, Net imports, Nuclear, Other fossil, Other renewables, Renewables, Solar, Total generation, Wind, Wind and solar. `Is aggregated source` is True for Total generation and Demand in the sample rows (Net imports is False); the page lists only "Clean, Fossil, Renewables, Total generation" as aggregates, so the adapter must key on the `Electricity source` value, not on the flag or the page. Flag values for Clean/Fossil/Renewables/Wind and solar were seen True in the ASEAN head rows. Rows per month: 16 for China, Russia and South Africa, 17 for EU, 16 or 17 for US. China and Russia have no `Other renewables` row; South Africa has no `Bioenergy` row (source sets differ per area). The Europe file has finer sources (e.g. `Onshore wind`), the global file has only `Wind`. Adapter rule: fail loudly if any header column is missing or renamed; tolerate a missing source per area.
- key needed: no (CSV). The API `https://api.ember-energy.org/v1/...` needs a free key ("No API key set", HTTP 403 unkeyed); not used.
- licence: "All content is released under a Creative Commons Attribution Licence (CC-BY-4.0)." (footer of https://ember-energy.org/data/monthly-electricity-data/ and other pages). Dedicated page https://ember-energy.org/creative-commons/ : "Ember content is released under a Creative Commons Attribution Licence (CC-BY-4.0) This means you're free to share and adapt our work – as long as you credit us. If you would like to use our logo, we ask that you request permission." Attribution wording: only "credit us"; no prescribed string found (suggest "Source: Ember, Monthly Electricity Data (CC-BY-4.0)" — this suggestion is ours, not Ember's). Underlying sources (EIA, Eurostat, Energy Institute or BP, national bureaus): whether each upstream permits Ember's redistribution is not confirmed; Ember's CC-BY statement covers "all content".
- known breaking changes: "Data download format update (July 2026)" confirmed on the page: one row per area, month and electricity source; metrics as columns; `Is aggregated source` flag; emissions intensity per source (overall on the `Total generation` row); area names simplified; membership columns TRUE/FALSE (in the file: True/False); source names sentence case. Old long-format parsers (Category/Variable) fail. Methodology PDF `https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf` (1,487,777 bytes, 2026-09-22) was downloaded but could not be text-extracted here; per-country method for China/Russia/South Africa: not confirmed. The page's "Last Updated 28/07/2026" text is stale.
- date checked: 2026-09-29. Fixtures: `monthly_generation_global_sample.csv`, `monthly_generation_europe_head.csv`.

## EMBER-2. Yearly electricity data (annual electricity demand by country, for basket weights)
- code/route: "Yearly Electricity Data" (https://ember-energy.org/data/yearly-electricity-data/); `https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_yearly_global.csv` (16,084,305 bytes, Last-Modified Tue 22 Sep 2026 16:24:55 GMT, ETag `67122835394a3edc9da6e56901f3d640`).
- cadence: page: "Updated monthly"; also "twice a month" in its own text. Not further verified.
- lag (latest period today): year 2025 for all five areas. History start: China 1985, Russia 1985, EU 2000, South Africa 2000, US 2000.
- units: same columns as monthly but `Year` instead of `Date` (values `2025`) and an extra `Capacity (GW)` column. Demand is `Electricity source` = `Demand`, value in `Generation (TWh)` (TWh per year). 2025 Demand: China 10,486.272; EU 2,774.435; Russia 1,177.295; South Africa 236.84; United States 4,532.142 TWh. 2025 Total generation: China 10,505.74; EU 2,798.415; Russia 1,193.989; South Africa 242.76; US 4,519.79 TWh. File has 224 areas (97,937 country rows, 6,266 region rows), 104,203 rows.
- header: `Area,ISO 3 code,Year,Area type,Electricity source,Is aggregated source,Generation (TWh),Generation YoY change (TWh),Generation YoY change (%),Share of generation (%),Share of generation YoY change (% points),Capacity (GW),Emissions (MtCO2e),Emissions YoY change (MtCO2e),Emissions YoY change (%),Share of emissions (%),Emissions intensity (gCO2e/kWh),Continent,Ember region,EU member,OECD member,G20 member,G7 member,ASEAN member` (24 columns). So yes, Ember provides annual electricity demand for all five regions.
- key needed: no. licence: as EMBER-1. Breaking changes: the July 2026 format change applies (page wording says "per area, month" but the yearly file has one row per area, year and source). date checked 2026-09-29. Fixture: `yearly_generation_global_sample.csv`.

## EMBER-3. European wholesale (day-ahead) electricity prices
- code/route: dataset "European Wholesale Electricity Price Data" (https://ember-energy.org/data/european-wholesale-electricity-price-data/). Files under `https://files.ember-energy.org/public-downloads/price/outputs/`: `european_wholesale_electricity_price_data_monthly.csv` (118,947 bytes, Last-Modified 2026-09-29T09:12:35Z), `..._daily.csv` (3,612,735 bytes, 2026-09-29T09:11:52Z), `..._hourly.zip` (42,018,516 bytes, 2026-09-29T09:16:49Z; contains `all_countries.csv` 172,090,669 bytes plus 32 per-country CSVs).
- cadence: page says "Updated monthly"; the files were regenerated on 2026-09-29 and contain the current partial month and days to 2026-09-28, so refresh appears to be at least daily (update schedule not stated: not confirmed).
- lag (latest period today): monthly 2026-09 (PARTIAL month; a running average); daily 2026-09-28 (United Kingdom 2026-09-27); hourly latest not measured (only the head of the zip was read).
- history start: 2015-01 for 23 countries (Austria, Belgium, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Italy, Latvia, Lithuania, Luxembourg, Netherlands, Norway, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden) and Switzerland (from 2015-01 but 133 of 141 months); later: United Kingdom 2016-06, Bulgaria 2016-10, Serbia 2016-12, Croatia 2017-10, Ireland 2018-10, Montenegro 2023-04, North Macedonia 2023-05, Albania 2026-07. 32 countries; no EU aggregate row (the adapter must build one, with its own weights); there are gaps (e.g. Switzerland 133 monthly rows vs 141; Greece and Netherlands 4,281 of ~4,289 daily rows).
- units: `Price (EUR/MWhe)`. Headers: monthly and daily `Country,ISO3 Code,Date,Price (EUR/MWhe)` (Date `YYYY-MM-01` monthly, `YYYY-MM-DD` daily); hourly `Country,ISO3 Code,Datetime (UTC),Datetime (Local),Price (EUR/MWhe)`. Note the ISO column is `ISO3 Code` here but `ISO 3 code` in the generation files. Example: United Kingdom 2026-09 monthly 154.94; Switzerland 2026-09-28 daily 198.66.
- key needed: no.
- licence: "All content is released under a Creative Commons Attribution Licence (CC-BY-4.0)." (footer of the price page) and https://ember-energy.org/creative-commons/ (quote in EMBER-1). Methodology quote: "Hourly data is sourced from ENTSO-e, EMR (UK), SEMOpx (Ireland). Missing values are interpolated from nearby values. This data is then aggregated to produce average daily and monthly values per country, weighted by load. In countries with multiple exchanges (for example, a 15-minute exchange and a separate 60-minute exchange), the average is taken." Also: "these are the prices generators receive for selling electricity on the spot market. They are not the same as the prices paid by electricity consumers". ENTSO-E's own reuse terms for the underlying data: not confirmed.
- known breaking changes: ENTSO-E day-ahead moved to 15-minute resolution on 2025-10-01 (desk note, not re-verified here); Ember states it averages multi-exchange countries. Interpolated values are in the series. The latest month is partial.
- date checked: 2026-09-29. Fixtures: `price_monthly_sample.csv`, `price_daily_sample.csv`, `price_hourly_head.csv`.

## Not re-verified in this task
- Ember carbon price viewer (Montel-sourced) and its lack of a download: not re-checked; leave the desk note as "not confirmed".
- EIA Electric Power Monthly Table 5.6.A and its "preliminary" wording: not read.
- EIA API v1 retirement, exact throttle values, revision behaviour of EIA-930: not confirmed.

---

# Part C: FX, commodities, carbon

Checked 2026-09-29 (UTC evening) from the cloud session, keyless, through the agent proxy, TLS verification on.
Every claim below was re-verified by a live request today unless marked "not confirmed". Fixtures and their
exact request URLs, fetch times and sha256 are in `fixtures/<source>/MANIFEST.json`.
Tags: [T] = tested today with a live request; [P] = read on a primary page today; [X] = not confirmed.

---

## A. ECB euro foreign exchange reference rates (EXR)

- **Code / series key:** dataflow `EXR`, key `FREQ.CURRENCY.CURRENCY_DENOM.EXR_TYPE.EXR_SUFFIX`.
  - Daily: `D.USD.EUR.SP00.A`, `D.CNY.EUR.SP00.A`, `D.ZAR.EUR.SP00.A` (and `D.RUB.EUR.SP00.A`, suspended). [T]
  - Monthly average: `M.USD.EUR.SP00.A`, `M.CNY.EUR.SP00.A`, `M.ZAR.EUR.SP00.A`. Attribute COLLECTION = "A" (Average of observations through period). [T]
  - The desk-research key (`D.USD+CNY+RUB+ZAR.EUR.SP00.A`) is correct. The monthly key is the same with `M.`. Multi-currency `+` works. [T]
  - The monthly value equals the simple arithmetic mean of the daily values: 2026-08 USD, mean of 21 daily obs = 1.1593095238095241 = the M value. [T, computed from fixtures]
- **Endpoint:** `https://data-api.ecb.europa.eu/service/data/EXR/{key}?startPeriod=..&lastNObservations=..&format=csvdata[&detail=dataonly]` (also jsondata, SDMX-ML default). Structure: `https://data-api.ecb.europa.eu/service/dataflow/ECB/EXR?references=children` (200). [T]
- **Cadence:** daily on TARGET working days; monthly. Unit: currency units per 1 EUR (UNIT_MULT 0, 4 decimals). Series title complement says "2.15 pm (C.E.T.)". [T]
- **Lag (latest period today, 2026-09-29):** daily latest = 2026-09-29 (USD 1.1355, CNY 7.6117, ZAR 18.5887), Last-Modified header 2026-09-29 13:56:59 GMT (page text says "usually updated at around 16:00 CET"; the data were live earlier than that). Monthly latest = 2026-08 (September not yet published because the month is incomplete). [T]
- **History start:** daily USD, RUB, ZAR 1999-01-04; CNY 2000-01-13. Monthly USD, RUB, ZAR 1999-01; CNY 2000-01. [T]
- **RUB:** last daily observation 2022-03-01 (117.201); last monthly observation 2022-02 (88.890995; no 2022-03 monthly average published). Page text (verbatim): "Owing to current trading activity in the EUR/RUB market, the European Central Bank (ECB) is not in a position to set a reference rate that is representative of prevailing market conditions. The ECB has therefore decided to suspend its publication of a euro reference rate for the Russian rouble until further notice. The ECB last published a EUR/RUB reference rate on 1 March 2022." (the "on 1 March 2022" tail is partly split across markup in my extract; the series data confirm 2022-03-01). [T][P]
  URL: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html
- **Key needed:** no.
- **Licence:** ECB "Disclaimer & copyright", https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html [P]. Verbatim:
  > "Copyright © for the entire content of this website: European Central Bank, Frankfurt am Main, Germany."
  > "Subject to the exception below, users of this website may make free use of the information obtained directly from it subject to the following conditions:"
  > "When such information is distributed or reproduced, it must appear accurately and the ECB must be cited as the source."
  > "If the information is modified by the user (e.g. by seasonal adjustment of statistical data or calculation of growth rates) this must be stated explicitly."
  (also a condition on information incorporated in documents that are sold: buyers must be told it is free from the ECB site). Note: this is a custom attribution licence, not CC. It does not say "non-commercial" anywhere; "free use" is granted. The desk-research summary "non-commercial" was wrong. The data-api / data portal pages I opened (data.ecb.europa.eu/help/api/overview) only link to this same "Disclaimer & Copyright"; an API-specific licence: not found.
  Cross-rates USD/CNY and USD/ZAR derived via EUR count as "modified" data: state it on the site.
- **Caveats:** the ECB page says "The reference rates are published for information purposes only. Using the rates for transaction purposes is strongly discouraged." [P]. Rates are the 14:10 CET concertation rates (page) / "2.15 pm" (series title), a point observation, not a daily average.
- **Known breaking changes:** RUB suspended from 2022-03-01. Bulgarian lev removal on 2026-01-01 (page comment; irrelevant here). Response header `cache-control: max-age=30`. [T]
- **Date checked:** 2026-09-29.
- **Fixtures:** `fixtures/ecb/` (8 files, 64 KB): last-1 with full metadata for the 4 currencies, daily USD/CNY/ZAR since 2026-06-01 (dataonly), monthly since 2022-01 (dataonly), RUB first/last, history-start files, text extract of the ECB page and disclaimer sections (raw HTML not stored, >100 KB each).

---

## B. Bank of Russia (cbr.ru) official RUB rates

- **Code / series key:** `R01235` USD, `R01375` CNY, `R01810` ZAR (CBR internal ids; `R01239` EUR); look up via `https://www.cbr.ru/scripts/XML_val.asp?d=0` (200). [T]
- **Endpoints (all keyless, all reachable from here, all 200):** [T]
  - Latest daily set: `https://www.cbr.ru/scripts/XML_daily.asp` (Content-Type `application/xml; charset=windows-1251`; English names: `XML_daily_eng.asp`).
  - A given date: `XML_daily.asp?date_req=dd/mm/yyyy` (tested 15/09/2026).
  - History of one currency: `https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=dd/mm/yyyy&date_req2=dd/mm/yyyy&VAL_NM_RQ=R01235`.
  - These are documented by the Bank of Russia on its "Technical resources / Getting data using XML" page (https://www.cbr.ru/development/SXML/ [T]). That page states: "* если параметр(date_req) отсутствует, то Вы получите документ на последнюю зарегистрированную дату" (if date_req is missing you get the latest registered date).
  - JSON: no official JSON endpoint found. `XML_daily.asp?...&json=1` still returns XML. `https://www.cbr.ru/dataservice/` returned 404. [T] (Third-party JSON mirrors are not in SOURCES.md and were not used.)
  - Monthly averages: none found on cbr.ru. The `currency_base/monthly/` page is the pre-2010 "rates set monthly (until 11.01.2010)" legacy, not averages. Compute monthly means from `XML_dynamic` daily records. [T]
- **Fields:** `<Nominal>` (units the rate is for, e.g. ZAR 10, JPY 100, KZT 100), `<Value>` (decimal comma, RUB per Nominal), `<VunitRate>` (RUB per 1 unit, decimal comma, may use E notation e.g. `5,15329E-05`). `VunitRate` is present today; the desk research did not mention it. Use VunitRate or Value/Nominal. [T]
- **Cadence / lag:** each business day; the rate is dated the day it takes effect, published the day before. Today (2026-09-29) `XML_daily.asp` returned Date="30.09.2026" (USD 84.4283, CNY 12.5764, ZAR nominal 10 value 51.4274); `XML_dynamic` for 01-30/09/2026 already had a 30.09.2026 record. The English page says "has set from 30.09.2026 ... without assuming any liability to buy or sell foreign currency at the rates below". The "Last updated" shown is 29.09.2026. Saturday records exist in the dynamic series (26.09.2026 present). [T]
- **History start:** USD `XML_dynamic` first record 01.07.1992 (125,26). [T] Redenomination break: values through 30.12.1997 are in old roubles (5960 RUB/USD), from 01.01.1998 in new roubles (5,96) - 1000:1, so pre-1998 values need /1000 (tested for USD). [T]
- **Units:** RUB per Nominal units of foreign currency.
- **Key needed:** no. Rate limits: none stated on the pages read (not found). robots.txt (`/robots.txt` 200) disallows only /search/, a few PDFs and SaveToPdf; it does not restrict /scripts/. [T]
- **Licence / reuse:** no data-specific licence found. The site's User Agreement (https://www.cbr.ru/eng/user_agreement/, "Last updated on: 03.12.2019") [P], verbatim:
  > "Materials of the Website may only be used with the consent of the rightsholders."
  > "The link to the Website is mandatory when quoting any materials from the Website, including copyrighted works."
  and "This User Agreement ... is applicable to all information available on the Website." No open licence, no statement about data reuse or commercial use. => **reuse status: not confirmed / consent-of-rightsholder wording; link to cbr.ru is mandatory when quoting.** Treat as: cite and link, and ask Bank of Russia (or take legal advice) if redistributing the series. (Desk research said "User Agreement text could not be fetched, /eng/about/privacy/ 404": the correct URL is /eng/user_agreement/.)
- **Known breaking changes:** 1998 redenomination; monthly-set rates ended 11.01.2010; since Feb-Mar 2022 the official rate is a capital-controls-era rate (interpretive, not a data break). New `VunitRate` element present. [T]
- **Date checked:** 2026-09-29.
- **Fixtures:** `fixtures/cbr/` (9 files, 68 KB): untrimmed raw windows-1251 XML for latest, latest-eng, 2026-09-15; XML_dynamic for USD/CNY/ZAR Sept 2026; USD 1990-1992 history-start; text extract of user agreement and the rates-page disclaimer.

---

## C. World Bank Commodity Price Data ("Pink Sheet")

- **Code / series key (sheet "Monthly Prices", column labels verbatim):** `Coal, Australian` ($/mt), `Coal, South African **` ($/mt), `Natural gas, US` ($/mmbtu), `Natural gas, Europe` ($/mmbtu), `Liquefied natural gas, Japan` ($/mmbtu), `Natural gas index` (2010=100). Row label format `YYYYMmm`, e.g. `2026M08`. Missing values are "…". [T]
  Columns after 89 in total; row 5 = names, row 6 = units, data from row 7. Other sheets: "Mismatch Details", "Monthly Indices", "Description", "Index Weights". [T]
- **Endpoint (keyless):** landing page https://www.worldbank.org/en/research/commodity-markets links, today, to:
  - Monthly XLSX: `https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx` (200, 586,735 bytes, `Last-Modified: Wed, 02 Sep 2026 20:17:37 GMT`, sha256 `9fdcfa8a2aed9a1bb545a10c1a5ce036c6a0acd4766f450424ca800b4b5a0225`). Sheet header row 4: "Updated on September 02, 2026". [T]
  - Annual XLSX `.../CMO-Historical-Data-Annual.xlsx` (link present on the landing page; not downloaded). [P]
  - Monthly PDF (2 pages, 238,929 bytes, sha256 `7f5bb6b819c49dc79bb07a3669f443ee1e92787477f7d0399185f96b4f75e437`): `.../related/CMO-Pink-Sheet-September-2026.pdf` (200). Values match the XLSX (e.g. gas Europe Aug 21.11). Not saved. [T]
  - The document id path (`74e8be41...-0050012026`) is the same for the 2026 files today but the desk research is right that it can change: resolve the link from the landing page (scrape the `href` containing `CMO-Historical-Data-Monthly.xlsx`) rather than hard-coding.
- **Cadence:** monthly. Landing page: "Latest Commodity Prices Published (09/02/2026)" and "Next update: October 2, 2026". Data Catalog record: "Commodity prices are updated in the second business day of the month." [P]
- **Lag:** latest month in file = 2026M08 (published 2026-09-02, i.e. 2 days after month end). September 2026 data expected 2026-10-02. [T]
- **History start:** Natural gas, US 1960M01; Natural gas, Europe 1960M01 (0.4); Coal, Australian 1970M01; Coal, South African 1984M01; LNG Japan 1977M01; gas index 1977M01. (Desk research said coal history from 1960: wrong, coal starts 1970 / 1984.) [T]
- **Units:** nominal US$ ("monthly series are available only in nominal US dollars"). Values are monthly averages (not stated on the sheet; not confirmed).
- **Latest values today:** 2026M08: Coal AU 135.2, Coal ZA 96.8, gas US 2.77, gas Europe 21.11, LNG Japan 13.94; 2026M07 gas Europe 18.06. Matches desk research. [T]
- **Definitions (Description sheet, verbatim in fixture):** "Natural Gas (Europe), from April 2015, Netherlands Title Transfer Facility (TTF); April 2010 to March 2015, average import border price and a spot price component, including UK; during June 2000 - March 2010 prices excludes UK." Coal Australia: "from February 2022, port thermal, f.o.b. Newcastle, 6000 kcal/kg futures price. From 2015 to January 2022 ... spot price". Coal South Africa: "from January 2015, f.o.b. Richards Bay, NAR, 6,000 kcal/kg ... forward month 1" and "June to November 2022, March, April, June to September, December 2023, and January-May 2024 are estimates based on similar benchmarks". LNG Japan: "recent two months' averages are estimates". Sources cited: Bloomberg Finance L.P., World Gas Intelligence, Coal Week, Official Statistics of Japan. [T]
- **Revisions (new finding):** the workbook's "Mismatch Details" sheet lists cells that differ from the previous upload: for 2026M07 LNG Japan moved 11.8 -> 13.85 and the gas index 128.9 -> 130.3 (plus non-energy items). So the latest 1-2 months of LNG are revised the next month; Natural gas Europe and both coal columns were not in the mismatch list for the latest update. [T]
- **API route:** none found for these series. World Bank API v2 `https://api.worldbank.org/v2/sources` lists 71 sources (200); source 15 "Global Economic Monitor" (lastupdated 2026-09-08) has 36 indicators, none commodity (only stock-market ones); a scan of all 29,544 indicator names found no natural-gas or coal price indicator; `PNGASEU` as an indicator id is invalid. [T] So the XLSX/PDF is the only keyless route. The Data Catalog record (below) lists a "Download" section with the Commodity Markets website only.
- **Key needed:** no.
- **Licence:** Data Catalog record "Commodity Prices - History and Projections" (https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections, "Metadata last updated on May 14, 2025") [P]: "License: Creative Commons Attribution 4.0 ... This dataset is licensed under Creative Commons Attribution 4.0"; classification "Public"; "This dataset includes data previously published as the "Global Economic Monitor (GEM) Commodities" and "Manufactures Unit Value Index (MUV Index)"." Note the record lists Periodicity "Annual" (metadata slip; the Pink Sheet itself is monthly).
  Terms of Use for Datasets (https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets, which redirects to https://www.worldbank.org/ext/en/legal/terms-conditions/datasets) [P], verbatim:
  > "Unless specifically labeled otherwise, these Datasets are provided to you under a Creative Commons Attribution 4.0 International License (CC BY 4.0), with the additional terms below."
  > "You agree to provide attribution to The World Bank and its data providers in the following format: The World Bank: Dataset name: Data source (if known)."
  > "Some datasets and indicators are provided by third parties, and may not be redistributed or reused without the consent of the original data provider, or may be subject to terms and conditions that are different from those described above. Where applicable, these conditions are included in the dataset or indicator metadata."
  Also: no endorsement / no use of World Bank name or logo; the CC BY additions include a mediation/arbitration clause (https://datacatalog.worldbank.org/public-licenses).
  => **CC BY 4.0 confirmed at the dataset-record level** (this settles the desk research's "not confirmed"). Residual risk: the underlying prices come from Bloomberg / World Gas Intelligence / Coal Week; no third-party restriction is stated in the record or in the workbook (I found none in the XLSX Description or the PDF text), but the Terms carry the third-party exception. Attribution to use: "The World Bank: Commodity Price Data (The Pink Sheet): Bloomberg, World Gas Intelligence, Coal Week (data sources per Description sheet)".
  The general site Terms (https://www.worldbank.org/ext/en/legal/terms-conditions) restrict non-Dataset "Materials" to non-commercial and no derivatives; they defer to the dataset terms for Datasets listed in the Data Catalog. The Pink Sheet PDF carries no licence text (checked its text). [P][T]
- **Known breaking changes:** Europe gas is TTF only from 2015-04 (before: border-price/spot mix); Australia coal changes from spot to futures 2022-02; South Africa coal partly estimated for named months in 2022-2024; LNG last two months are estimates; document id in the URL changes.
- **Date checked:** 2026-09-29.
- **Fixtures:** `fixtures/worldbank/pink_sheet_monthly_gas_coal_last36.csv` (last 36 months 2023M09-2026M08 + 4 title rows + name and unit rows; 6 relevant columns only), `pink_sheet_history_starts.csv`, `licence_and_description_extract.txt`. Full xlsx not saved (586,735 bytes > 500 KB); full-file sha256 recorded in MANIFEST notes.

---

## D. Free TTF / coal alternatives (gas and coal benchmarks)

Best free reusable monthly TTF-based series: **World Bank "Natural gas, Europe"** (CC BY 4.0, above). No free daily TTF with a clear reuse licence was found. Checked:

1. **IMF Primary Commodity Price System (PCPS)** [T]
   - Endpoint (keyless): `https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS,9.0.0/{key}` with header `Accept: application/vnd.sdmx.data+csv;version=1.0.0`. Dims: COUNTRY.INDICATOR.DATA_TRANSFORMATION.FREQUENCY. Key `G001.PNGASEU.USD.M` (Natural gas, EU: "Natural Gas, Netherlands TTF Natural Gas Forward Day Ahead, US$ per Million Metric British Thermal Unit"), `G001.PCOALAU.USD.M` (Australian thermal coal, 12,000 btu/lb, FOB Newcastle/Port Kembla), `G001.PCOALSA.USD.M` (South African export price). `detail=dataonly` trims the metadata columns. Structure: `.../datastructure/IMF.RES/DSD_PCPS?references=descendants`. The legacy `dataservices.imf.org` endpoint failed here (proxy CONNECT 502). Dataset UPDATE_DATE 2026-09-08. History start 1992-M01 for all three (TTF DA series presumably spliced before its native start: "splicing" is mentioned in IMF metadata; native start not confirmed).
   - Latest: PNGASEU 2026-M08 20.922, 2026-M07 17.93 (World Bank: 21.11, 18.06 - close but not identical). Coal differs materially: PCOALAU 2026-M08 140.51 vs WB 135.2; PCOALSA 109.44 vs WB 96.8 (different benchmark definitions). Do not mix the two providers in one series.
   - Licence: API `LICENSE` field: "© International Monetary Fund Copyright. All Rights Reserved. https://www.imf.org/external/terms.htm". Terms page (https://www.imf.org/en/_site_imf/about/copyright-and-terms; the `/en/About/copyright-and-terms` URL returned 403 Access Denied to curl, the `_site_imf` path returned 200) names "Primary Commodity Prices" as covered "Data" and says, verbatim: "You may download, extract, copy, create derivative works, publish, distribute, and use Data obtained from IMF Sites, subject to the following conditions:" ... "when Data is distributed or reproduced in any manner, it must appear accurately with attribution to the IMF as the source, e.g. "Source: International Monetary Fund, Database Name, <<link to the dataset>>."" ... "If the Data is materially transformed by the User, this must be stated explicitly along with the required source citation." and finally "For any potential commercial reuse of IMF Data, please email copyright@imf.org to request permission." Also "Some statistical products may incorporate information from third parties and may have separate terms and conditions for usage." => free reuse with attribution; commercial reuse is a grey area (the last sentence). Weaker than CC BY. Second choice / cross-check.
   - Fixtures: `imf_pcps_ttf_coal_last36_monthly.csv`, `imf_pcps_first_obs.csv`, `imf_pcps_dataset_metadata_row.csv`, `imf_terms_extract.txt` in `fixtures/worldbank/` (request header noted in the manifest).
2. **Ember** [T/P]: European electricity prices & costs tool shows TTF, API2 coal and EUA (front December) but says "Price data sourced from Montel" (commercial) and offers no price download (its "Datasets used in this tool" is the ENTSO-E wholesale day-ahead electricity prices only). Site is "released under a Creative Commons Attribution Licence (CC-BY-4.0)" but the Montel data is not offered as a download. The old carbon price tracker was replaced by that page, and old API URLs (api.ember-climate.org/v1/carbon-price, api.ember-energy.org/v1/carbon-price) return 404. Not usable.
3. **ECB, Eurostat:** ECB data API has no gas/carbon price series in what I queried (EXR only checked). Eurostat: scanned all 8,149 dataflow names in the ESTAT catalogue for carbon/allowance/ETS/emission-trading: none is a price (only CO2 footprints and unrelated "tax allowances"). No TTF at Eurostat (retail gas prices only, not benchmark). [T]
4. **EIA:** Henry Hub daily/monthly (needs key, out of scope here; not checked).
5. **Commercial (not usable):** ICE Endex TTF, Bloomberg, Montel, Platts, Argus: not opened.

---

## E. EU carbon price (EUA)

**Conclusion: no free, reusable, machine-readable EUA price series with a clear open licence was found.** Checked today:

| Candidate | What I found | Verdict |
|---|---|---|
| EEX EUA primary auction report | Keyless download works: `https://public.eex-group.com/eex/eua-auction-report/emission-spot-primary-market-auction-report-2026-data.xlsx` (200, 69,470 bytes, Last-Modified 2026-09-29 09:02 GMT); history zip `.../Archive_Reports/emission-spot-primary-market-auction-report-2012-2025-data.zip` (766 KB per page). Latest auction in the 2026 file: 2026-09-29, auction price 84.87 EUR/tCO2 (columns: Date, Time, Auction Name, Contract, Status, Auction Price €/tCO2, Min/Max bid, Mean, Median, Volume, ...). Data are auction clearing prices, several auctions/week (Mon-Fri, some days DE/PL-specific), not a daily secondary spot. BUT licence: EEX disclaimer (https://www.eex.com/en/disclaimer): "Neither this website nor the contents made available therein ... may be copied, reprinted, published, transmitted, transferred, disseminated or distributed in any manner without the prior written approval of EEX AG. However, the preparation of a single copy for exclusive personal, non-commercial use ... are expressly permitted." and "Any commercial use shall only be permitted with the express written approval of EEX AG." EEX Licensing & Policies (https://www.eex.com/en/market-data/licensing-policies) sells Internal / External (Commercial, Media, Scientific) usage licences for EEX market data. => **Not open-licensed. I did not store the file in git (redistribution would breach these terms); it was only inspected in the scratchpad.** Best "lawful route": ask EEX for written permission or use the Media Usage licence ("disseminate the EEX Market Data publicly in raw form only ... price tickers on a public website"). Licence text of the file itself: not found beyond the site terms. |
| ICAP Allowance Price Explorer | EU ETS: EEX auction and ICE end-of-day (chart only); "Weekly average ICE Data is available for download and with a 6-month lag". Terms verbatim: "Graphics or underlying data provided by the ICAP Allowance Price Explorer may only be reproduced, redistributed and used for non-commercial purposes subject to ICAP's prior written permission." plus an ICE notice: "ANY DISTRIBUTION OR COMMERCIAL USE OF ICE FUTURES DATA IS PROHIBITED WITHOUT THE PRIOR WRITTEN CONSENT OF ICE DATA LLP." Prices updated "manually and quarterly". => No. |
| Ember | see D.2: EUA "front December contract ... sourced from Montel", chart only, no download; old API dead. | No |
| Instrat (energy.instrat.pl/en/prices/eu-ets/) | "Own representation by energy.instrat.pl • Data: EEX"; "License: Creative Commons Attribution 4.0 International (CC BY 4.0) - unless stated otherwise". No download/API found on the page. Underlying EEX terms apply, so CC BY on the charts does not clear EEX data. | No (chart only, upstream is EEX) |
| Sandbag Carbon Price Viewer | Chart only, "up to April 2026" (not current); sourced from Quandl (to 2009) then ICAP; no licence statement or download found. | No |
| Eurostat | No EUA price dataflow among 8,149 ESTAT dataflows checked. | No |
| World Bank Carbon Pricing Dashboard | `carbonpricingdashboard.worldbank.org` returned HTTP 403 from here (not worked around). Per search summary only, prices are recorded on 1 April each year: annual, event-only. Licence: not confirmed. | Not confirmed; annual at best |
| IMF PCPS | no carbon/EUA indicator among PCPS codes I listed (only gas and coal matched my search); not exhaustively checked. | No |
| European Commission (climate.ec.europa.eu auctioning / carbon market report) | Not confirmed: auctioning page URL 404, another page 429 (rate limit); Carbon Market Report not opened. | Not confirmed |
| EEA / EUTL | Emissions and allocations only, no prices (from desk research, not re-verified). | No |

Options for the index (for Ziggy): (a) omit the carbon component or show it as "no source"; (b) request written permission or a Media Usage licence from EEX and use auction clearing prices (monthly mean of auctions, volume-weighted); (c) an annual figure from a documented official source once its licence is confirmed. Do not use Montel/ICE/Investing-derived numbers.
Fixture: `fixtures/carbon/carbon_licence_extracts.txt` (licence/reuse lines only, no prices) + MANIFEST.

---

## Hosts blocked / unreachable from this environment (today)
- `dataservices.imf.org`: proxy CONNECT 502 (legacy IMF API); `api.imf.org` works.
- `www.imf.org/en/About/copyright-and-terms`: 403 Access Denied (Akamai); the `/en/_site_imf/about/copyright-and-terms` path works. No workaround beyond using a listed alternate path of the same public page.
- `carbonpricingdashboard.worldbank.org`: 403.
- `climate.ec.europa.eu` page: 429 once.
- Everything else opened (ecb, cbr.ru, worldbank.org, thedocs.worldbank.org, datacatalog.worldbank.org, api.worldbank.org, eex.com, public.eex-group.com, icapcarbonaction.com, ember-energy.org, energy.instrat.pl, sandbag.be, ec.europa.eu/eurostat) returned 200.
- Proxy status showed unrelated relay failures for atsenergo.ru and cec.org.cn (other tasks).

## Differences from the desk research (SOURCES.md 9-11)
1. Pink Sheet licence is now confirmed: the Data Catalog record states CC BY 4.0. Coal history starts 1970 (Australia) and 1984 (South Africa), not 1960; only US and Europe gas start 1960.
2. ECB licence has no "non-commercial" wording; ECB monthly averages exist (`M.` keys, simple mean of daily), monthly latest is 2026-08. ECB page says update "around 16:00 CET", series title says 2.15 pm.
3. CBR: `VunitRate` field exists; correct User Agreement URL is /eng/user_agreement/, text found (consent of rightsholders; link to site mandatory); no monthly averages; no JSON; 1998 redenomination in history; USD history begins 1992-07-01.
4. New: IMF PCPS has a keyless TTF (PNGASEU) and coal series via api.imf.org with free-reuse-with-attribution terms (commercial reuse: ask). World Bank Pink Sheet has no API route.
5. New: the Pink Sheet workbook flags revisions to the latest month (LNG Japan July 11.8 -> 13.85).
6. EUA: EEX auction files are downloadable keyless but not open-licensed; Ember carbon tracker no longer exists as a separate download (replaced by a chart page, Montel-sourced).

---

# Part D: US ISO day-ahead prices

Date checked: 2026-09-29 (UTC 19:21 to 19:31), from the build environment, curl via the pre-configured proxy, TLS verification on, no keys, no logins. About 6 requests per host or fewer, several seconds apart for OASIS. "Latest period" is relative to 2026-09-29.

Fixtures: `/home/user/Four-Corners-Index/fixtures/us_iso/` (13 files, 128 KB, `MANIFEST.json` with sha256). Nothing committed. Nothing outside `fixtures/us_iso/` and this file was written.

## Bottom line

The US has no single day-ahead price. Seven ISOs/RTOs run day-ahead markets (ISO-NE, NYISO, PJM, MISO, SPP, ERCOT, CAISO), and vast areas (the Southeast, most of the West) have no day-ahead market at all.

Of the seven, only two publish under terms that clearly allow public redistribution of prices:

| Operator | Reachable keyless | Reuse clearly allowed | History for monthly means | Verdict |
|---|---|---|---|---|
| ERCOT | Yes (last ~31 days only, HTML) | **Yes** (explicit) | Blocked (client-certificate wall / registration) | Licence OK, history blocked |
| CAISO | Yes (API, last 39 months) | **Yes, with credit** | 2023-07 onward keyless; 2016 onward needs a page I cannot reach | Licence OK, history partial |
| NYISO | Yes, 2000-11 onward | **No grant found** ("not confirmed") | Excellent | Data OK, licence unresolved |
| MISO | Yes (files, ~2023-01 onward) | Not confirmed (terms page behind Cloudflare challenge) | ~3.7 years | Licence unresolved |
| ISO-NE | No (403 on CSV, account for web services) | **No** (copyright asserted) | Not reached | Blocked |
| SPP | Not confirmed (JS app, endpoints not found) | Non-commercial only; commercial needs written authorisation | Not reached | Blocked/ambiguous |
| PJM | No (API 401; site tool member-restricted) | **No** (redistribution prohibited without membership) | Not reached | Blocked |

No free reusable aggregated compilation was found (see "Compilations" below).

**Recommendation for the US Wholesale cell: "no source" at STOP-1 for the headline index.** A composite from ERCOT + CAISO alone would cover 2 of 7 ISOs, exclude PJM (largest by load), and have no history before 2023-07 (CAISO) / none at all (ERCOT) without forward accumulation. If Ziggy wants a US number anyway, the only defensible option is a clearly labelled partial composite, defined at the end of this file. The unlocking action is human: ask NYISO, MISO, ISO-NE and SPP for written permission, or accept NYISO's facts-only position.

---

## Per-source findings

### NYISO (New York)

- **code/series:** Day-Ahead Market (DAM) zonal LBMP, report P-2A. Names: CAPITL, CENTRL, DUNWOD, GENESE, HUD VL, LONGIL, MHK VL, MILLWD, N.Y.C., NORTH, WEST (11 in-state zones), plus 4 external proxies (H Q, NPX, O H, PJM). Columns: Time Stamp, Name, PTID, LBMP ($/MWHr), Marginal Cost Losses, Marginal Cost Congestion.
- **endpoint (daily):** `https://mis.nyiso.com/public/csv/damlbmp/YYYYMMDDdamlbmp_zone.csv` (HTTP 200, 16,798 bytes for 2026-09-27)
- **endpoint (monthly archive):** `https://mis.nyiso.com/public/csv/damlbmp/YYYYMM01damlbmp_zone_csv.zip` (2015-01: 134,046 bytes, 31 daily CSVs)
- **cadence:** daily, one file per delivery day, 24 hourly rows x 15 names.
- **lag:** the day-ahead file for tomorrow is already posted. 20260930 returned 200 (16,864 bytes); 20261001 returned 404. Latest period: 2026-09-30 (delivery day).
- **history start:** monthly zip for 2000-11 returned 200 and contained `20001101damlbmp_zone.csv`. So 2000-11 onward; 2015-01 confirmed by download. Daily files are not kept long: 20250101 and 20150101 daily URLs returned 404, so backfill must use the monthly zips.
- **units:** $/MWh (header "LBMP ($/MWHr)"). Timestamps are Eastern local time (00:00 to 23:00 on 09/27/2026).
- **key needed:** none.
- **licence:** NO data licence found. Only the Legal Notice speaks to reuse, https://www.nyiso.com/legal-notice: "Access to this Web site does not confer any license or ownership interest in either the form or content of the Web site, including any confidential or proprietary information or intellectual property of any kind or nature, and the NYISO hereby expressly reserves such rights and property in its entirety." The next sentence restricts only images/video: "Downloading, republishing, retransmitting, reproducing, or other use of any image or video on this website as a stand-alone file is strictly prohibited". The MIS index pages (`mis.nyiso.com/public/`, header, menu, P-2Alist) contain no terms. Commercial/public redistribution of prices: **not confirmed** (no grant, no prohibition on data files). Treat as "ask NYISO" rather than "free to reuse".
- **breaking changes seen:** file format differs by era. 2015 files have every field double-quoted and a truncated congestion header (`"Marginal Cost Congestion ($/MWH...`); 2026 files are unquoted with full headers. Use a real CSV parser and match columns by position or normalised name.
- **aggregation notes:** external proxies (H Q, NPX, O H, PJM) must be excluded from a NY average. Load weights per zone: not measured here (NYISO load data is a separate keyless report, not fetched).
- **fixtures:** `nyiso_damlbmp_zone_20260927.csv`, `nyiso_damlbmp_zone_20150101.csv`, `nyiso_licence_extract.txt`.
- **date checked:** 2026-09-29.

### CAISO (California)

- **code/series:** OASIS `PRC_LMP`, `market_run_id=DAM`. Trading hubs `TH_NP15_GEN-APND`, `TH_SP15_GEN-APND`, `TH_ZP26_GEN-APND` tested (72 LMP rows for 3 hubs x 24 h). Load-aggregation-point nodes (DLAP_*) not tested.
- **endpoint:** `https://oasis.caiso.com/oasisapi/SingleZip?queryname=PRC_LMP&market_run_id=DAM&node=<node,node,...>&startdatetime=YYYYMMDDTHH:MM-0000&enddatetime=...&version=1&resultformat=6` returns a zip holding a CSV. Multiple nodes accepted in one call (3 tested). Per-request window limits: not tested, not confirmed.
- **cadence:** daily DAM, hourly values. Response carries LMP, MCC, MCE, MCL, MGHG rows (5 types); LMP is the price.
- **lag:** 2026-09-29 delivery day returned 24 rows at 19:30 UTC. 2026-09-30 returned 0 rows at 19:27 UTC (CAISO DAM results not yet posted). Latest period: 2026-09-29, with tomorrow's result posted later in the afternoon Pacific time.
- **history start (keyless API):** rolling window of about 39 months. 2023-07-15, 2023-10-15, 2023-12-15, 2024-01-15 returned 24 rows; 2023-01-15, 2022-01-15, 2020-01-15, 2018-01-15, 2015-01-01 returned "No data returned for the specified selection" (error 1000). The OASIS home page says: "To download historical data that is beyond 39 months, and as far back as 2016, see the Historical OASIS Data Downloader." That downloader is on developer.caiso.com, which returned 403 to curl, and the same page says "Self-registration is required to access the site." Not worked around. History before ~2023-07: **not confirmed / not reachable**.
- **units:** MW column holds the price in $/MWh (column named `MW` in this report; unit not printed in the response, taken from the OASIS report definition: not confirmed on the response). Timestamps in GMT plus `OPR_DT`/`OPR_HR` Pacific operating day and hour.
- **key needed:** none for `oasisapi`. Self-registration on developer.caiso.com for the downloader and API specs.
- **licence:** https://www.caiso.com/privacy-terms-of-use, Terms of Use: "Most of the materials and information contained on this Website and the California ISO mobile application were generated, compiled or assembled from materials and information that are freely available for public use consistent with the general policies of the Public Records Act (California Government Code section 6250, et seq.), as provided by California Public Utilities Code section 345.5, and may be used by you provided that you keep intact all copyright, trademark and other proprietary notices and that you credit the California ISO when using such materials and/or information." Redistribution of prices with attribution: **allowed on the face of the text**. Caveats: the preceding paragraph says "No material or information from this Website ... may be copied, reproduced, republished ... except (i) as authorized in these Terms of Use"; the separate API Terms (updated 08/22/2019) say "CAISO owns all right, title and interest in and to the CAISO API and CAISO Data" and grant a "revocable, non-exclusive, non-sublicenseable, non-transferable, limited license"; whether the API Terms govern the `oasisapi` endpoint is **not confirmed**. Credit line to use: "California ISO (OASIS)".
- **breaking changes:** the API Terms say "CAISO will occasionally make changes to its API, including backwards incompatible changes" and "parts of the CAISO API are undocumented". The endpoint above is the `oasisapi` v1 form; a 2015 request returned an XML error inside the zip (not CSV), so the parser must check the member's extension.
- **fixtures:** `caiso_prc_lmp_dam_hubs_20260927.csv` (LMP rows only, trimmed), `caiso_licence_extract.txt`.
- **date checked:** 2026-09-29.

### ERCOT (Texas)

- **code/series:** NP4-190-CD "DAM Settlement Point Prices" (report type 12331): "The Settlement Point Prices for all Resource Nodes, Load Zones, and Trading Hubs from the Day-Ahead Market." Public display page carries hubs HB_BUSAVG, HB_HOUSTON, HB_HUBAVG, HB_NORTH, HB_PAN, HB_SOUTH, HB_WEST and load zones LZ_AEN, LZ_CPS, LZ_HOUSTON, LZ_LCRA, LZ_NORTH, LZ_RAYBN, LZ_SOUTH, LZ_WEST. Historical product: NP4-180-ER "Historical DAM Load Zone and Hub Prices" (zip, xlsx; weekly; first run 2011-10-01).
- **endpoint (keyless, reachable):** `https://www.ercot.com/content/cdr/html/YYYYMMDD_dam_spp.html` (HTML table, 24 rows x 17 columns, 23 KB). Not CSV.
- **endpoint (not reachable):** `https://mis.ercot.com/misapp/GetReports.do?reportTypeId=12331...` and `.../13060...` and `https://mis.ercot.com/public/data-products/markets/day-ahead-market?id=NP4-190-CD` all 302 to `mis.ercot.com/siteminderagent/cert/.../smgetcred.scc`, a SiteMinder client-certificate step; curl got an SSL handshake failure. Not worked around. `https://api.ercot.com/api/public-reports/...` 302 to a "Loading" page (authentication; ERCOT's API needs registration, **not confirmed** in detail). `https://data.ercot.com/data-product-archive/NP4-190-CD` returned a JS shell (200) and `.../NP4-180-ER` a 302; contents not confirmed.
- **cadence:** daily, one DAM run per operating day.
- **lag:** page for 2026-09-28 was live with the note "Last Date and Time: Sep 27, 2026 12:52". Tomorrow (2026-09-29 and 09-30 pages) not tested; the display offers "Today" and "Tomorrow" tabs. Latest period tested: 2026-09-28.
- **history start (keyless):** only about 31 days: 20260901 returned 200 with data ("Last Date and Time: Aug 31, 2026 12:33"); 20150115 returned 404. The product page lists "Display Duration 31". Full history since 2010-11-29 (product first run date) exists but is behind the certificate wall or the registered API: **not reachable here**.
- **units:** table headers do not print units; ERCOT product definition and market convention are $/MWh: **not confirmed on the page**.
- **key needed:** none for the display page; registration for the API (not confirmed); MIS "public" area blocked from here.
- **licence:** https://www.ercot.com/help/terms (last updated 07/20/2023), clause 5: "The publicly available contents of this website may be used, reproduced, and redistributed, provided that the contents are not modified and that you maintain all copyright and other notices contained in the contents, including this Agreement. Notwithstanding the foregoing, raw data provided in public portions of this website may be used, reproduced, and redistributed in compilations, charts, and analyses without maintaining such notices." Public redistribution of prices, including in derived indices: **allowed**. Clause 6 forbids use that "negatively affects the performance of this website"; be gentle. Clause 9: the ERCOT logo/name marks need written permission.
- **breaking changes:** none observed in one fetch. The old MIS pages appear to be giving way to the Data Portal API (data.ercot.com, api.ercot.com); not confirmed.
- **fixtures:** `ercot_dam_spp_display_20260928.html` (raw), `ercot_dam_spp_20260928.csv` (derived from it), `ercot_licence_extract.txt`.
- **date checked:** 2026-09-29.

### MISO (Midcontinent)

- **code/series:** `da_expost_lmp` market report. Rows are Node, Type, Value, HE 1 to HE 24. Types: Gennode (1,718 nodes), Hub (424), Interface (46), Loadzone (440), each with LMP, MCC (congestion), MLC (loss) values. Eight named hubs: ARKANSAS.HUB, ILLINOIS.HUB, INDIANA.HUB, LOUISIANA.HUB, MICHIGAN.HUB, MINN.HUB, MS.HUB, TEXAS.HUB. (The 424 "Hub" rows include many aggregate pricing nodes, not just these eight.)
- **endpoint:** `https://docs.misoenergy.org/marketreports/YYYYMMDD_da_expost_lmp.csv` (1,190,435 bytes for 2026-09-27; Azure blob, last-modified 2026-09-26 18:19 GMT).
- **cadence:** daily, one file per delivery day.
- **lag:** HEAD requests: 20260930 returned 200 (posted), 20261001 returned 404. Latest period: 2026-09-30 (not downloaded; existence only).
- **history start (keyless):** files exist for 2023-01-15 (200), 2023-07-15, 2024-01-15 etc.; 2022-10-15, 2022-07-15, 2022-01-15, 2020-01-15, 2015-01-15 return 404. So roughly 2023-01 onward, exact boundary between 2022-10-15 and 2023-01-15 not pinned down. Older annual archives: **not confirmed** (the market-reports page that would list them is behind a Cloudflare challenge; guesses at annual file names returned 404).
- **units:** $/MWh presumed; the file does not print a unit ("not confirmed on the file"). Hours Ending are EST (fixed, no DST) per the file preamble ",,,All Hours-Ending are Eastern Standard Time (EST)".
- **key needed:** none.
- **licence:** **NOT CONFIRMED.** `www.misoenergy.org` (market reports page and terms page) returned HTTP 403 with `cf-mitigated: challenge` (Cloudflare "Just a moment..."); not worked around. The data files carry no licence text. A web-search summary (secondary, unverified) says the MISO Legal and Privacy page bars users from "reproduce, create derivative works of, distribute, publicly perform, publicly display or in any way exploit any of the materials or content on the MISO Website". Treat as not reusable until someone reads https://www.misoenergy.org/meet-miso/legal-and-privacy/ in a browser.
- **breaking changes:** none observed.
- **fixtures:** `miso_da_expost_lmp_hubs_20260927.csv` (8 hubs, LMP only, trimmed from 1.19 MB), `miso_licence_NOT_CONFIRMED.txt`. Delete the data fixture if MISO's terms turn out to bar it.
- **date checked:** 2026-09-29.

### ISO-NE (New England)

- **code/series:** ISO Express pricing reports (Hourly Day-Ahead LMPs, Monthly LMP Indices, Weekly LMP Indices). Web services: RESTful, `https://webservices.iso-ne.com/api/v1.1`, XML or JSON.
- **endpoint:** the page lists `/transform/csv/monthlylmpindex?year=YYYY` (years 2019 to 2026 listed) and the report tree at `www.iso-ne.com/isoexpress/web/reports/pricing/-/tree/...`.
- **cadence, lag:** not confirmed (data not reached).
- **history start:** the Monthly LMP Indices page lists 2019 to 2026 links; earlier years not confirmed.
- **units:** not confirmed (not reached).
- **key needed:** Web services: yes, an ISO-NE account ("you will need to be signed up for Web Services to access the WADL", https://www.iso-ne.com/participate/support/web-services-data). Public CSV: none required in principle, but from here `https://www.iso-ne.com/transform/csv/monthlylmpindex?year=2019` returned HTTP 403 (47 bytes) and `.../transform/csv/hourlylmp/da?...` returned 404. Not worked around.
- **licence:** https://www.iso-ne.com/legal-privacy: "You are also hereby put on notice that the Content is protected by copyright under United States laws. Any duplication of the Content or non-personal use may violate copyright, trademark, and other laws." (where "Content" is defined as "all information and data on this website".) Also: "To request permission to use a graph, chart, or other image on this website, please email info@iso-ne.com." Redistribution of prices: **not allowed without permission**.
- **fixtures:** `isone_licence_extract.txt` only.
- **date checked:** 2026-09-29.

### SPP (Southwest Power Pool)

- **code/series:** DA LMP by location (Marketplace portal `https://portal.spp.org/pages/da-lmp-by-location`).
- **endpoint:** the portal is a JavaScript single-page app (200, 609-byte shell). My guesses at `portal.spp.org/file-browser-api/...` and `marketplace.spp.org/file-browser-api/...` returned 404. Data endpoint, cadence, lag, history start, units: **not confirmed**.
- **key needed:** not confirmed.
- **licence:** https://www.spp.org/terms-conditions/, Copyright section: "Permission is implicitly granted to copy and distribute (via computer network or printed form) in whole or in part (with appropriate citation) EXCEPT when such materials will be used, in whole or in part, within a commercial publication (printed or otherwise) or when the author(s) or SPP will be quoted in commercial materials, forums or publications. Any commercial use of these materials requires prior, express written authorization from the author(s) or a duly authorized officer of SPP." A free public non-profit dashboard may not be "commercial", but that is a legal reading for Ziggy, not for me. Status: **ambiguous; ask SPP**.
- **fixtures:** `spp_licence_extract.txt` only.
- **date checked:** 2026-09-29.

### PJM (PJM Interconnection)

- **code/series:** Data Miner 2 feed `da_hrl_lmps` (hourly DA LMPs), `https://api.pjm.com/api/v1/da_hrl_lmps` returned HTTP 401 without a key. The site `https://dataminer2.pjm.com/feed/da_hrl_lmps` returns a JS app shell (200).
- **cadence, lag, history, units:** not confirmed (not reached).
- **key needed:** yes, a PJM account: "Automatic queries can be received with a PJM account through the Data Miner application program interfaces (API)." (https://www.pjm.com/markets-and-operations/etools/data-miner-2). No account was created.
- **licence:** same page: "Information and data contained in Data Miner is for internal use only and redistribution of information and or data contained in or derived from Data Miner is strictly prohibited without an active PJM Membership. A minimum level of Associate Membership is required." Also "Non-members may not exceed 6 data connections per minute." Redistribution: **prohibited** for non-members. The linked PDF "Acceptable Terms of Use" (https://www.pjm.com/-/media/DotCom/etools/edatafeed/data-license-agreement-edata-feed-data-miner-2.pdf, 104,439 bytes) was downloaded but **not read** (no PDF text tool here); the web-page sentence is what is quoted.
- **fixtures:** `pjm_licence_extract.txt` only.
- **date checked:** 2026-09-29.

---

## Compilations (free, reusable, aggregated)

- **EIA "Wholesale Electricity Market Portal" (launched March 2024):** the EIA page https://www.eia.gov/electricity/wholesalemarkets/ describes it as covering the seven ISOs with day-ahead LMPs, and links a YouTube demo. I found no data download or API on that page; **not confirmed as a machine-readable source**. EIA's separate hub prices remain the ICE-republished set (already ruled out); the EIA Electricity Monthly Update "Regional Wholesale Markets" page shows only ranges of daily on-peak prices at selected locations in charts.
- **Ember:** no US wholesale price series (SOURCES.md already notes this; not rechecked).
- **IEEE DataPort / Mendeley "Global Day-Ahead Electricity Price Dataset":** lists CAISO, ERCOT, ISO-NE, MISO, NYISO, PJM, SPP among 40 countries. IEEE DataPort: "This dataset requires an IEEE DataPort Subscription to access" (login, not free). The Mendeley copy (DOI 10.17632/s54n4tyyz4.3, version 3, published 2025-09-19) is labelled CC BY 4.0, but the page does not state per-market provenance, aggregation, date range or resolution; the files list was not visible. It is a static snapshot, so it cannot update a monthly index, and an aggregator's CC BY label does not override PJM's or ISO-NE's terms. **Not usable; not confirmed.**
- **NREL "Electricity Market and NREL ATB Resources" (CKAN mirror, CC BY):** a catalogue of links to CAISO OASIS, ERCOT MIS and the ATB; no dataset of prices in itself. Not a source.
- **LBNL (Berkeley Lab) Wind/Utility-Scale Solar market reports:** search returned only report pages with XLS data files for early years; whether those contain ISO/hub price series and under which licence is **not confirmed**, and they are annual, so not a monthly index input.
- **FERC, DOE open data, gridstatus.io:** not checked in this pass. Not confirmed.

## Proposed composite (only if a US number is wanted)

There is no single US day-ahead price. Any US figure is a construction, and must be labelled as one.

**Definition "US (reusable ISOs), partial":** monthly mean of day-ahead prices, per ISO, then a load-weighted mean across ISOs whose terms allow redistribution.

1. Per ISO monthly price:
   - ERCOT: mean of hourly `HB_BUSAVG` (ERCOT's bus-average hub), or better, load-zone prices weighted by zone load.
   - CAISO: mean of hourly `TH_NP15`, `TH_SP15`, `TH_ZP26` (generation trading hubs), or DLAP nodes if they turn out to be available (not tested).
   - If Ziggy secures permission: NYISO 11 in-state zones weighted by zone load; MISO the eight named hubs or load zones; add ISO-NE, SPP, PJM only with written permission or membership.
2. Weights: each ISO's annual energy demand from a source with a clear licence (EIA-930 via the EIA API at G3 would fit; **weights not measured here, no numbers stated**). Fixed for a calendar year to avoid month-to-month reweighting jumps.
3. Publish coverage next to the number: which ISOs are in, and their share of US demand (not measured here).

**Limits, stated honestly:**
- Coverage is 2 of 7 ISOs today (ERCOT, CAISO), and PJM, the largest, is excluded by its terms. Non-ISO areas (Southeast, much of the West) have no day-ahead market and are outside any such index.
- Hub and generation-trading-hub prices are not what consumers or loads pay; load-zone or load-aggregation prices are closer.
- Timestamps differ (Eastern local for NYISO, EST fixed for MISO, GMT plus Pacific for CAISO, ERCOT local); monthly means need each ISO's own operating-day convention.
- History: no keyless history reaches 2015-01 for the two clearly reusable ISOs. CAISO gives about 39 months back (to ~2023-07); ERCOT gives ~31 days. Earlier history would need the CAISO downloader (registration) and ERCOT's certificate-gated or registered data. A base period in 2015 is not achievable from these two; the series would begin when collection starts, or from 2023-07 for CAISO.
- Year-on-year comparison is not possible for ERCOT for at least a year of forward collection.
- The composite is not comparable to the EU Ember series (Ember averages country day-ahead prices; this would average selected hubs/zones).

## What would change the answer

1. Written permission from NYISO (no grant now), MISO (terms unread), ISO-NE (copyright), SPP (commercial reuse). NYISO has the best data (history to 2000-11, keyless, monthly zips) and is the strongest candidate to ask.
2. Someone reading https://www.misoenergy.org/meet-miso/legal-and-privacy/ in a browser (Cloudflare blocks curl).
3. A registration for the ERCOT API and the CAISO developer site, if Ziggy is willing to create accounts (this session cannot and should not).

## Unverified items, as asked (all "not confirmed")

CAISO per-request window limit; CAISO DLAP node availability; CAISO API Terms scope; CAISO history before ~2023-07; ERCOT units on the display page; ERCOT API registration detail; ERCOT `data.ercot.com` archive access; MISO terms text and annual archives; MISO units; ISO-NE public CSV contents, units, history; SPP endpoints and history; PJM PDF terms text, cadence, history; NYISO load-zone weights; US demand weights; EIA portal data access; LBNL price data; FERC and gridstatus.io.

---

# Part E: China, Russia, South Africa

Method: curl through the session proxy, TLS verification always on, User-Agent naming the project, 1-3 requests per host, no retries around a block. Fixtures in `fixtures/china/`, `fixtures/russia/` and `fixtures/southafrica/` (each with `MANIFEST.json`; Russia also `NO_SOURCE.md`). Tags: [T] = read from a response fetched today; [S] = search-engine snippet only, not fetched; "not confirmed" = not read from a fetched response. Times UTC, 2026-09-29 ~19:00-19:20.

## Host reachability (owner action list)

| Host | Result | Reason (as seen) |
|---|---|---|
| rosstat.gov.ru | TLS failure | server sends leaf only, issued by "Russian Trusted Sub CA"; not in system/proxy trust store; NOT bypassed |
| gks.ru | TLS failure | same |
| atsenergo.ru, www.atsenergo.ru | connection reset after ~12 s (3 tries) | proxy log `ws_closed_mid_exchange`; consistent with geo-block, cause not proven |
| www.np-sr.ru (Market Council) | proxy 502 on CONNECT | policy denial or upstream failure |
| fedstat.ru / www.fedstat.ru | HTTP 403 | app-level Forbidden |
| data.stats.gov.cn (NBS data query) | HTTP 403 | WAF "UrlACL" |
| www.cec.org.cn (China Electricity Council) | connection reset | proxy `ws_closed_mid_exchange` |
| www.sgcc.com.cn, js./ha./sd./zj./sh.sgcc.com.cn, pmos.sx.sgcc.com.cn | reset / 502 / 405 | State Grid and its provincial sites all unreachable |
| gd.csg.cn, pm.gd.csg.cn | 502 / no answer | Guangdong Power Grid primary site |
| jgs.ndrc.gov.cn | 502 on CONNECT | NDRC price department sub-site |
| fgw.beijing.gov.cn, fgw.sc.gov.cn, fzggw.jiangsu.gov.cn, fzggw.zj.gov.cn, fgw.shandong.gov.cn, www.miit.gov.cn | reset / 502 | provincial DRCs of Beijing, Sichuan, Jiangsu, Zhejiang, Shandong |
| fgw.henan.gov.cn | HTTP 403 (HEAD) | |
| www.baqiao.gov.cn | reset | Xi'an district mirror of Shaanxi notices |
| www.statssa.gov.za | HTTP 200 but an Imperva/Incapsula bot-challenge stub (JS), for both the site and `/publications/P0141/CPIHistory.pdf` | not worked around |
| dataservices.imf.org | 502 | (seen in proxy log, not part of this task) |
| Reachable (200) | www.stats.gov.cn, www.ndrc.gov.cn, www.nea.gov.cn, www.gov.cn, www.95598.cn, www.csg.cn, drc.gd.gov.cn, fgw.sh.gov.cn, pds.gov.cn, www.shantou.gov.cn, www.so-ups.ru, www.minenergo.gov.ru, www.cbr.ru, data.gov.ru, www.eskom.co.za, www.nersa.org.za, www.ntcsa.co.za, energy.ec.europa.eu, www.globalpetrolprices.com | |

---------------------------------------------------------------------
# SOUTH AFRICA (badge B proposed)

No wholesale market exists. Eskom direct tariffs are official, machine-readable (XLSM) and annual; municipal tariffs (most households) are not collected centrally.

## ZA-1. Eskom tariff workbook and Schedule of Standard Prices (household and industrial list tariffs)
- **code/series:** Eskom "Eskom-tariffs-1-April-2026-Public.xlsm" (38 sheets; e.g. `Homelight NLA`, `Homepower NLA`, `Businessrate NLA`, `Megaflex NLA`, `Miniflex NLA`, plus `Munic` sheets), the "Tariffs and Charges Booklet 2026/2027" PDF and the "Schedule of standard prices" PDF. [T] all three downloaded (xlsm 466,672 B; booklet 4,125,094 B; schedule 7,208,097 B). In the schedule PDF the tables are images (no text layer); the booklet and the workbook carry the numbers as text/cells.
- **endpoint:** page `https://www.eskom.co.za/distribution/2026-2027-tariff-increase/` links the files:
  - `https://www.eskom.co.za/distribution/wp-content/uploads/2026/03/Eskom-tariffs-1-April-2026-Public.xlsm` (Last-Modified 2026-03-11)
  - `https://www.eskom.co.za/distribution/wp-content/uploads/2026/07/Eskom-Tariff-booklet_Final.pdf` (2026-07-06)
  - `https://www.eskom.co.za/distribution/wp-content/uploads/2026/03/20260226-Schedule-of-standard-prices-for-01-April-2026-Public-1.pdf` (2026-03-17)
  - previous year booklet found by search, fetched: `https://www.eskom.co.za/distribution/wp-content/uploads/2025/06/Tariff-booklet.pdf` (2025-06-13). File names change every year (no stable URL): the pipeline must scrape the landing page.
- **cadence:** annual. Non-local-authority (Eskom direct) tariffs 1 April to 31 March; local-authority (municipal bulk) tariffs 1 July to 30 June. Schedule states 8.76% for direct customers from 2026-04-01 and 9.01% for municipal bulk from 2026-07-01 [T, schedule p.2].
- **lag:** none (published before the year starts). Latest period today: tariff year 2026/27 (from 2026-04-01).
- **history start:** the tariff books for older years were not located as a linked archive. The "Tariff history" page (`https://www.eskom.co.za/distribution/tariffs-and-charges/tariff-history/`) [T] links only 1970-2007 PDFs and the historical-average XLSX (ZA-2). Homelight 20A c/kWh confirmed for two years only: 2025/26 = 216.11 (248.53 incl VAT), 2026/27 = 235.04 (270.30 incl VAT) [T, 216.11*1.0876 = 235.04]. An earlier back-series can be derived from Eskom's published per-tariff % increases in ZA-2 (2008/09 onward), flagged "derived".
- **units:** c/kWh, excl. and incl. 15% VAT; R/POD/day, R/kVA/month for fixed charges.
- **key needed:** no.
- **licence/terms:** Eskom website terms (Sep 2021) clause 2.1: "Eskom licenses the User to view, download and print the content of the Eskom website, provided that such content is used for private, personal, educational and/or non-commercial purposes only." Clause 2.2: "Content from the Eskom website may not be used or exploited by Users for any commercial and non-private purposes without the prior written consent of Eskom." Clause 2.10: no person may use "applications (including web crawlers, robots or web spiders) to search, collect or copy content from the Eskom website, for any purposes, without the prior written consent of Eskom." Clause 2.8: "Users may quote small and reasonable amounts of content ... subject to such a quote being placed in inverted commas and acknowledged." URL: https://www.eskom.co.za/wp-content/uploads/2021/10/WEBSITE-TERMS-AND-CONDITIONS_Sep2021.pdf (linked from https://www.eskom.co.za/about-eskom/website-terms-and-conditions/). The booklet disclaimer adds "No representation or warranty is given regarding the accuracy". **Consequence: automated daily fetching and republishing on a public dashboard needs Eskom's prior written consent (electricitypricing@eskom.co.za is the pricing contact named in the schedule). Owner decision.** Fixtures here are small extracts (quotation).
- **known breaking changes:** FY2027 restructure: Generation Capacity Charge fixed portion raised from 20% to 30%; Homepower/Homeflex service and admin charge fixed portion 33.33% to 66.66% [T, schedule p.2]. Municipal tariff (Municrate) merged former Businessrate/Landrate/Homepower for local authorities. A `#REF!` cell exists in the Megaflex sheet (AF2). Homelight no longer has the block above 350 kWh (2025/26 change, [S]).
- **date checked:** 2026-09-29. **badge:** B (official, machine-readable, tariff-derived, annual, terms need consent).
- **fixtures:** `eskom_tariffs_2026-04-01_workbook_extract.csv`, `eskom_tariff_booklet_2026-27_extract.txt`, `eskom_tariff_booklet_2025-26_homelight_extract.txt`, `eskom_website_terms_extract.txt`.

Measured values, 2026/27, non-local authority, c/kWh excl. VAT [T, workbook and booklet agree]:
- Homelight 20A 235.04; Homelight 60A 298.79 (single energy charge).
- Homepower 1/2/3/4: energy 280.05 + ancillary 0.45 + network demand 28.68 = 309.18 variable, plus fixed R/day charges (Homepower 1: network capacity R13.19, service+admin R5.74, generation capacity R1.09 per POD per day).
- Businessrate 1-3: energy 242.90 + ancillary 0.45 + network demand 15.81, plus fixed charges; electrification/rural subsidy 5.37 and affordability subsidy 5.10 c/kWh are separate columns (the booklet applies them to some tariffs).
- Megaflex (>1 MVA, time-of-use), voltage 500 V to <66 kV, distance <=300 km: high-demand season (Jun-Aug) peak 720.19 / standard 180.05 / off-peak 120.03; low season (Sep-May) 298.89 / 168.05 / 120.03; legacy 24.14 c/kWh; plus generation capacity R12.27/kVA/m, transmission network R11.15/kVA/m, ancillary 0.42 c/kWh, service R215.91/POD/day, admin R21.07/POD/day, electrification 5.37, affordability 5.10 c/kWh. (Full matrix by voltage and distance in the fixture.) An all-in Megaflex c/kWh is NOT measured: it depends on load factor and NMD; none was computed here.

**Proposal, household:** two-layer.
1. *List-tariff series (preferred, "tariff-derived"):* Eskom Homelight 20A c/kWh excl. VAT, annual step on 1 April, applied to the 12 months April-March. VAT policy to match the EU/US household definition (taxes included): show incl. 15% VAT (2026/27 = 270.30 c/kWh). Caveat: Homelight is the subsidised 20 A prepaid tariff for low-usage supplies, not an "average household". Alternative "typical" is Homepower 1 with a stated consumption (e.g. 350 kWh/month) using variable + fixed charges; a consumption assumption is required and must be declared.
2. *Realised average (for history and cross-check):* Eskom "Residential" average price c/kWh sold, FY, from ZA-2 (2025/26 = 273.79 c/kWh; 2015/16 = 108.11).
Caveats: Eskom direct residential sales are 9,043 GWh in 2025/26 against 78,275 GWh sold to local authorities (ZA-2), so most South African households pay a municipal tariff, not an Eskom one (municipal tariffs: ZA-3). South Africa sits beside the basket, not in it, so B is acceptable.

**Proposal, industrial:** Megaflex (>1 MVA, time-of-use) is Eskom's large industrial/mining tariff; Miniflex (25 kVA to 1 MVA) is the mid-size urban one and the closer match for "typical mid-size band". Neither has a single c/kWh. Proposal: (a) history and level from ZA-2, "Industrial (Excl NPA)" realised average price (2025/26 = 212.03 c/kWh; 2015/16 = 70.52), which excludes negotiated pricing agreement (NPA) customers; note the plain "Industrial" row (163.58 in 2025/26) includes NPA volumes at much lower prices and its sales fell from 43,153 to 33,457 GWh in one year because of that reclassification [T]; (b) a declared Megaflex or Miniflex reference bill for the forward tariff year is a G2/G4 design choice. Caveats: annual only; excl. VAT (business recovers VAT); excludes municipal industrial customers and private wheeling.

## ZA-2. Eskom "Historical average prices and increase" workbook
- **code/series:** `Historical-average-prices-and-increase.xlsx`, sheet "Historical trend": revenue (Rm), sales volumes (GWh) and average price (c/kWh sold) by customer class: Local-authorities, Residential, Commercial, Industrial, Mining, Agriculture, Traction, International, NPA, "Industrial (Excl NPA)", "Average standard tariff price (Excld NPA and Int'l)"; annual % price adjustment; NERSA standard-tariff increase; per-tariff April increases (Urban, Rural, Homepower, Homelight 20A/60A, Affordability subsidy charge); municipal 1 July increase; Eskom's application vs NERSA decision. [T]
- **endpoint:** `https://www.eskom.co.za/distribution/wp-content/uploads/2026/09/Historical-average-prices-and-increase.xlsx` (270,427 B, Last-Modified 2026-09-03), linked from the Tariff history page. URL has a year/month folder; scrape the page.
- **cadence:** annual, updated after the financial-year results. **lag:** FY 2025/26 (ended 2026-03-31) published 2026-09-03, about 5 months. Latest period today: 2025/26.
- **history start:** 2003 (calendar-year column), then 2004/05 onward, fiscal years April-March. Requirement "monthly/annual series back to 2015": available annually from 2015/16 to 2025/26 for average price and volumes; monthly would repeat the annual value (no monthly).
- **units:** c/kWh (nominal, excluding VAT, not stated in file; revenue/sales basis), GWh, Rm, fractions for %.
- **key needed:** no. **licence/terms:** same Eskom website terms as ZA-1 (quote above); terms not more specific for this file.
- **known breaking changes:** "Industrial" and "NPA" split, Eskom volume drops in 2022/23 and 2025/26 from NPA and Industrial reclassification; `IAS 18 revenue reversal` and other reconciling lines; 2003 column is a calendar year. Values are Eskom direct customers (plus local authorities as bulk buyers), not all South African consumption: total sales 2025/26 = 178,032 GWh.
- **date checked:** 2026-09-29. **badge:** B.
- **fixture:** `eskom_historical_average_prices_2010-11_to_2025-26.csv` (trimmed, long format).

## ZA-3. Municipal tariffs (about 40% of customers per desk research; not verified by me)
- **what was verified:** (i) Eskom schedule states municipal bulk purchase tariffs rise 9.01% from 2026-07-01 [T]; (ii) NERSA site (www.nersa.org.za, reachable) hosts regulator decisions and old public notices, including "Public notice on indicative municipal tariff guideline, benchmarks and timelines" for 2011-12 (`/file/300/...pdf`) [T on link, file not fetched]; (iii) search results say municipalities apply to NERSA by 31 March, NERSA decides by ~11 May, effective 1 July [S: engineeringnews 2026-03-13, energize.co.za]. Not found: any NERSA table of all approved municipal residential tariffs. "not confirmed".
- **feasibility:** each metro (City Power/Johannesburg, Tshwane, Cape Town, eThekwini, Ekurhuleni) publishes its own annual tariff PDF on its own site, with different block structures; this is a manual annual collection for a declared basket of 4-5 metros, badge B/C, not automatable as one feed. I did not fetch any metro site. Owner scope decision; not needed for launch since ZA is beside the basket.
- **licence/terms:** not confirmed (no municipal site was fetched; each metro publishes under its own terms). Eskom's website terms do not apply to municipal sites.
- **date checked:** 2026-09-29. **badge proposal:** C if added.

## ZA-4. NERSA (approvals)
- **series:** NERSA media statement / reasons for decision on Eskom retail tariff 2026/27; [S] URL `https://www.nersa.org.za/files/files/2026/03/MediaStatement-NERSAapprovesEskomRetailTariffsandStructuralAdjustmentapplicationfor2026-27.pdf` from desk research NOT fetched by me (the site now serves files as `/file/<id>/...`; the older pattern is unconfirmed). Eskom's own copy of the NERSA letter is linked on the Eskom 2026/27 page: `https://www.eskom.co.za/distribution/wp-content/uploads/2026/03/MediaStatement-NERSA-Letter.pdf` [T link, file not fetched].
- Reasons for decision for the 2025/26 tariff exist as `https://www.nersa.org.za/file/5862/EskomRetailTariffApplication_RFD_11March_2025.pdf` [T link on `/regulator-decisions`]. Content not read.
- **cadence:** annual (plus the 2026 redetermination after the R54.7bn RAB error [S]). **licence/terms:** terms not found on the pages read. **badge:** B (context, not a price series). Not used as a data source: the Eskom workbook already carries the approved tariffs.
- **date checked:** 2026-09-29. (links only; files not fetched)

## ZA-5. Eskom Data Portal (mix/demand, not prices)
- **endpoint:** `https://www.eskom.co.za/dataportal/`; bulk data via emailed link from `https://www.eskom.co.za/dataportal/data-request-form/` (form: name, email, institution, purpose; "Up to a maximum of 5 years"; personal information kept 6 months, POPIA) [T]. Not submitted (needs an email address and personal details; owner decision). Per-page CSV: the "Weekly energy demand" page advertises `https://www.eskom.co.za/dataportal/wp-content/uploads/2026/07/Weekly_Energy_Demand_Financial_Year.csv` but that URL returned **404** today [T], i.e. the page link is stale (differs from desk research, which did not test it).
- **licence/terms:** Portal disclaimer [T] `https://www.eskom.co.za/dataportal/disclaimer/`: "The information or data published or displayed remains the sole property of Eskom and may not be exploited by the User for any purposes, including but not limited to, commercial purposes." plus "any reproduction or use of the data in any manner or form is deemed as acceptance by the User of the terms of use of this site". The data is "indicative and subject to verification".
- **badge:** C (emailed link, manual, restrictive terms). Ember remains the mix source for ZA.
- **date checked:** 2026-09-29.

## ZA-6. Statistics South Africa CPI electricity item and electricity generated/available (P4141)
- Unreachable: www.statssa.gov.za returns an Imperva/Incapsula JavaScript challenge stub (212 B, `_Incapsula_Resource`) for the CPI publication page and the CPIHistory.pdf. Not worked around. CPI electricity index not confirmed. **badge:** would be A if reachable; here "unreachable from this environment (bot challenge)".
- **date checked:** 2026-09-29. (unreachable, bot challenge)
- **licence/terms:** not confirmed (site unreachable from this environment).

## ZA-7. Wholesale market
- No day-ahead market operates. NTCSA's SAWEM page [T] `https://www.ntcsa.co.za/sa-wholesale-electricity-market-sawem/`: portal description "Coming soon"; the page's countdown widget target is `Apr 01 2026 7:30:00 +0` and reads 00:00:00 today, so the 1 April 2026 date has passed without an operating market. The desk research's "April 2027" (pv-magazine 2026-07-23) is [S], not fetched. Eskom's own descriptions of the market: not fetched. Wholesale for ZA: "no market", as SPEC says. (Eskom's average price to local authorities, 206.22 c/kWh in 2025/26, is a regulated bulk retail tariff, not a market price; do not present it as wholesale.)
- **fixture:** `ntcsa_sawem_page_extract.txt`.

## ZA consumption for weights
Ember stays the choice for national consumption. Nothing better verified: Eskom sales total 178,032 GWh in 2025/26 (Eskom plus municipal bulk purchases, excludes private/wheeled and rooftop) is a cross-check only; Stats SA electricity-available statistics unreachable (ZA-6).

---------------------------------------------------------------------
# CHINA (badge C proposed)

Confirmed: there is **no** free official national average household or industrial price; no stable national or multi-province publication of catalogue tariffs or agency-purchase prices was found. What exists is per-province, per-month notices by the grid company, mirrored as PDFs on government sites. A documented provincial basket is feasible only for provinces whose notices are reachable, in PDF.
- **date checked:** 2026-09-29.
- **licence/terms:** not applicable; no market data exists to reuse.

## CN-1. Provincial agency-purchase (代理购电) prices for commercial and industrial users
- **code/series:** monthly "代理购电价格公示表" / "代理购电用户电价表" per grid company and province. Verified samples: State Grid Henan, Aug 2026 (`henan_agency_purchase_price_2026-08.pdf`) and China Southern Grid Guangdong, Apr 2026, Shantou area table (`guangdong_agency_purchase_price_2026-04_shantou.pdf`). [T]
- **endpoint:** Henan: `https://pds.gov.cn/upload/files/2026/7/29/2026年8月代理购电价格公示表.pdf` (Pingdingshan city government mirror, 231,037 B; URL embeds upload date and has a "水印版" variant in other months). Guangdong: `https://www.shantou.gov.cn/attachment/0/150/150864/2524702.pdf` (Shantou city government mirror, 185,695 B; one table per group of cities, so Guangdong has several tables). Primary publishers (ha.sgcc.com.cn, gd.csg.cn) unreachable. Search index also lists monthly files on baqiao.gov.cn (Shaanxi; host unreachable to me) and further pds.gov.cn months (Sep 2025 to Aug 2026) [S]. The notice pages for these mirrors have no stable listing, so monthly discovery would mean searching or guessing dated URLs: fragile.
- **cadence:** monthly, published about 3 days before the month starts (NDRC 809: prices "calculated monthly", announced 3 days ahead via the Guangdong price-list text [T]); Henan's Aug 2026 notice is dated 2026-07-28 [T]. **lag:** none (forward-looking). Latest confirmed: Aug 2026 (Henan), Apr 2026 (Guangdong-Shantou). Sept and Oct 2026 tables not found in the search index; not confirmed.
- **history start:** mechanism set by NDRC notice 发改办价格〔2021〕809号 (2021-10-23) [T: `https://www.ndrc.gov.cn/xxgk/zcfb/tz/202110/t20211026_1300892.html`, fixture `ndrc_notice_809_2021-10-23.html`]; Guangdong list confirms catalogue C&I prices abolished and monthly agency prices from 2021 [T]. Earliest downloadable month per province: not confirmed (Henan mirror back to at least Sep 2025 per [S]).
- **units:** CNY/kWh (Henan table; Guangdong table is fen/kWh and states 含税, tax included; the Henan text extract does not state tax status: not confirmed). Henan Aug 2026 [T]: agency purchase price 0.451405; line loss 0.021281; system operation 0.037029; levies 0.028889; flat all-in 1-10 kV single-tier "电度用电价格" 0.706604 (=0.451405+0.021281+0.168+0.028889+0.037029, checked); <1 kV 0.734104; time-of-use for <1 kV: peak 1.4224, high 1.1999, flat 0.7341, valley 0.3783. The notice also reports agency-purchased C&I volume 809,800 (unit 万千瓦时, i.e. 8.098 bn kWh) forecast for Aug and 69.77亿 kWh (6.977 bn kWh) actual for June 2026.
- **key needed:** no. **licence/terms:** none stated on the PDFs. Host terms: Guangdong DRC footer "版权所有：广东省发展和改革委员会 未经书面授权禁止复制或建立镜像" (copyright reserved; copying or mirroring without written authorisation prohibited) at https://drc.gd.gov.cn/spjg/content/post_846283.html [T]. Other hosts: terms not found. Public price notices are facts published for user information, but reuse terms are unverified; treat as "not confirmed".
- **known breaking changes:** the table layout changes by province and over time (Henan's tariff cycle "第四监管周期" from 2026 per 发改价格〔2026〕1077号, quoted in the Aug 2026 note; Guangdong table row order differs by group of cities). Extraction from PDF needs a PDF text library and a per-province parser; the text layer loses column headings (Henan p.1), so column mapping must be tested against the fixture.
- **date checked:** 2026-09-29. **badge:** C.
- **caveats:** covers only default-supplied C&I users ("暂未直接参与市场交易"; large 10 kV+ users are meant to buy in the market), a shrinking slice; the price is a component-based bill price, not the market price paid by all industry; commercial and industrial are not separated; each province has different voltage and TOU tables. Historical 1.5x multiplier for users that left the market (Henan note 3) is excluded from any "typical" value.

## CN-2. Household catalogue tariffs (居民阶梯电价), first tier
- **series:** provincial DRC notices; first-tier price (yuan/kWh) and annual first-tier volume. Verified [T]: Shanghai tier 1 (0-3120 kWh per household-year) **0.617 yuan/kWh** (<1 kV, non-TOU), tier 2 0.667, tier 3 0.917, per DRC notice 沪发改价管(2012)020 号 of 2012-06-15, republished at `https://fgw.sh.gov.cn/cmsres/20/207f6574daeb48949d247f39ec7a3322/dd80cd964bb1c65cd46d22caa85e55f3.pdf` (Last-Modified 2024-08-19); the notice says tier 1 is "not adjusted and basically stable for three years"; whether Shanghai changed it since 2012 was not checked, so 0.617 is "per the 2012 notice". Guangdong (Shantou list effective 2021-12-01) [T]: tier 1 **67.02 fen/kWh** (67.886875 with levies), tier 2 72.02, tier 3 97.02; `https://www.shantou.gov.cn/attachment/0/82/82778/2192164.pdf`. Sichuan tier 1 0.5224 yuan/kWh from 2026-07-01, and Beijing tier 1 0.4883, appear in search snippets only [S, official pages unreachable: fgw.sc.gov.cn, fgw.beijing.gov.cn].
- **cadence:** irregular, changed by provincial notice (rare); no monthly publication. **lag:** n/a. **history start:** 2012 national scheme (NDRC guidance; provinces 2012-2013). **units:** yuan/kWh, tax inclusive. **key needed:** no.
- **licence/terms:** terms not found (Guangdong DRC copyright line as in CN-1).
- **known breaking changes:** tier structures differ (summer/non-summer in Guangdong and Sichuan); Guangdong price list header cites 13+ amendment notices.
- **date checked:** 2026-09-29. **badge:** C.

## CN-3. National electricity consumption (weights and sector split)
- **series:** NEA monthly "全社会用电量" release via Xinhua [T]: Aug 2026 total 1,033.2 bn kWh (+1.7%), primary 16.9, secondary 612.4, tertiary 215.5, urban and rural residential 188.3 (-4.0%); Jan-Aug total 7,173.0 bn kWh (+4.3%), residential 1,113.2 bn (+0.3%). Endpoint `https://www.nea.gov.cn/20260924/9b291b0f1f524078855c63061fe5ced9/c.html` (page dated 2026-09-24; NEA told Xinhua on 2026-09-20). Fixture `nea_national_consumption_2026-08.html`.
- **cadence:** monthly, about 3 weeks after month end; **lag:** Aug 2026 latest. **history start:** not confirmed (each month is a separate news page with a different URL; no series table). **units:** 100 million kWh. **key needed:** no. **licence/terms:** not found on NEA pages read.
- **known breaking changes:** none observed. Better than Ember for China's weight? It is official, current and split by sector (residential vs industry), but only as narrative HTML in Chinese and one page per month; Ember stays the parseable weights source, NEA is the cross-check.
- **badge:** B (official, regular, but text-only, irregular URL).
- **date checked:** 2026-09-29.

## CN-4. NBS energy production (generation)
- `https://www.stats.gov.cn/english/PressRelease/202609/t20260916_1965338.html` [T]: Aug 2026 generation of industrial enterprises above designated size 943.8 bn kWh (-0.8% y/y); Jan-Aug 6,647.6 bn kWh (+2.4%); y/y rates by source; **no table of absolute TWh by source** (fixture `nbs_energy_production_2026-08.html`). Published 2026-09-16 (lag 16 days). The NBS data query (data.stats.gov.cn) returns 403 to us, so absolute series are unreachable.
- **licence/terms:** NBS Terms of Service (2022-09-06) `https://www.stats.gov.cn/english/nbs/200701/t20070104_59236.html` [T, fixture `nbs_terms_of_service.html`], III.1: "You are allowed to download and use the statistical data on this website." with II.3: reprinting "must be a reasonable and good faith quoting for the purpose of use of news or free public information" and attribution "Reprinted from (or quoted from) the website of the National Bureau of Statistics" with www.stats.gov.cn. **badge:** B/C for China mix (Ember is primary).
- **date checked:** 2026-09-29.

## CN-5. NDRC catalogue/agency policy
- NDRC 809 (2021-10-23) [T] states C&I users of 10 kV and above should buy directly in the market, others are supplied by the grid company's agency purchase, and residential and agricultural users are guaranteed volume/price supply. Confirms desk research and the rationale for badge C. Terms not found on the page.
- **date checked:** 2026-09-29.

## CN-6. Wholesale
- No national market. Provincial spot markets exist (Shanghai's DRC notices of 2026 on spot-market price limits and the "沪发改价管〔2026〕5号" appear in search results [S]); the exchange portals tested are unreachable or gated (`pmos.sx.sgcc.com.cn` 405, `pm.gd.csg.cn` no answer, www.cpem.org.cn reachable but not examined). China wholesale: "no national market" per SPEC; do not use a single province as the national value.
- **date checked:** 2026-09-29.
- **licence/terms:** not applicable; no national market data. Provincial exchange portals unreachable or gated.

## CN-7. International compilations
- **GlobalPetrolPrices** `https://www.globalpetrolprices.com/terms.php` [T]: site footer states "www.GlobalPetrolPrices.com is licensed under a Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported License". CC BY-NC-ND forbids commercial use and derivatives; a public index derived from it is not permitted. Terms body (subscription terms) did not render without JavaScript; not read. The China page was titled "December 2025", nine months stale today. **Excluded. Not scraped.** A "Download data / API" is a paid subscription. **badge:** n/a.
- **European Commission dashboards** (`https://energy.ec.europa.eu/data-and-analysis/energy-prices-and-costs-europe/dashboard-energy-prices-eu-and-main-trading-partners-2024_en`) [T]: state that annual Eurostat data is converted to monthly by Enerdata and wholesale comes from ENTSO-E, Enerdata EnerMonthly and S&P Platts; China figures come from those licensed vendors, no data download or reuse licence for them found. **Excluded.**
- **IEA** excluded (not freely reusable, per brief). **World Bank, ADB, Ember retail:** not checked by me (no China retail price series known to me; not confirmed). CEIC "36-city" price monitoring: licensed, not checked.

## China proposal
- **household:** first-tier catalogue tariff (yuan/kWh, tax inclusive) for a documented provincial basket. Verified-reachable and fixture-able today: Shanghai (0.617, 2012 notice) and Guangdong (0.6702 fen-converted, 2021 list). Candidate additions need their DRC host whitelisted or a different mirror: Jiangsu, Zhejiang, Shandong, Henan, Sichuan, Beijing. Weights by provincial household consumption: source not verified (data.stats.gov.cn 403); a constant-weights basket with a declared weights table is the honest option. Show as a level that changes only when a province re-issues its notice; carry-forward between notices is legitimate here (it is the tariff), flagged as "administrative price".
- **industrial:** agency-purchase all-in "电度用电价格" for 1-10 kV single-tier users (flat/TOU average) in the same provinces (Henan and Guangdong verified), monthly. Label "C&I default-supply users only, not industrial average". Sustaining this needs monthly discovery of PDFs on mirrors (fragile) or whitelisting the grid companies' hosts, if reachable from a non-Chinese address at all (State Grid hosts reset our connection: likely geo-block).
- **wholesale:** none nationally (say so).
- **weights (consumption):** NEA monthly national total and sector split (CN-3) for cross-check; Ember for the parseable series.
- **fallback if the owner will not accept two provinces:** "no source" for China retail/industrial; keep mix and consumption.

---------------------------------------------------------------------
# RUSSIA (badge C proposed; price sources unverified)

**Nothing on price could be fetched with TLS verification.** See `fixtures/russia/NO_SOURCE.md`. Desk research claims (Rosstat XLSX, sheet names, 13.7 MB) are "not confirmed": they were made with `-k`, which we must not use.

## RU-1. Rosstat average consumer prices, household electricity
- **series (from desk research, not confirmed):** "Электроэнергия в квартирах без электроплит за минимальный объем потребления, в расчете за 100 кВт.ч" and variants; monthly XLSX at `https://rosstat.gov.ru/storage/mediabank/sred_potreb_cen_08-2026.xlsx`; page `https://rosstat.gov.ru/statistics/price`.
- **status today:** TLS chain unverifiable from this environment (see host table). Search-engine results for `rosstat.gov.ru/storage/mediabank/...` show the host publishes monthly price releases (e.g. `.../135_02-09-2026.html`) [S] but not the specific XLSX. Cadence, lag (~11 days per desk research), history start, licence: **not confirmed**. Rosstat units per desk research: RUB per 100 kWh; convert to kWh by /100 if verified.
- **key needed:** no (per desk research). **licence/terms:** terms not found. **known breaking changes:** not confirmed. **date checked:** 2026-09-29. **badge:** C (administrative price in a national statistics file; access needs an owner decision on the CA).
- **household definition proposal:** the "without electric stoves, minimum consumption volume" per 100 kWh series as the lower band and the "electric stove" variant as an alternative; Russian household prices are regulated regional tariffs, tax included (VAT is in the tariff for households). Confirm once readable.

## RU-2. Industrial
- No industrial kWh price found. Rosstat producer-price statistics (indices; possibly an average producer electricity price) [S, not confirmed]. Ministry/ATS "HCE/nerc" style reports: no reachable file found. **Say "no source" for industrial** (SPEC agrees). Do not proxy with wholesale.
- **date checked:** 2026-09-29.
- **licence/terms:** not applicable; no industrial price source found.

## RU-3. Wholesale, ATS day-ahead (price zones 1 and 2)
- Unreachable (connection reset x3, see table). Geo-blocking is the likely cause; not proven. Terms: not seen. Market Council (np-sr.ru) 502. **No source** from this environment; if it stays that way, the site shows "no source" for wholesale Russia and the wholesale index is renormalised over the regions that have a market, as SPEC allows.
- **date checked:** 2026-09-29.

## RU-4. SO UPS annual statistics (consumption for weights)
- **series:** annual generation and consumption of the Russian energy system, `https://www.so-ups.ru/functioning/ups/ups2026/` [T]: 2025 consumption **1,177.3 bn kWh** (UES 1,161.3; isolated territories 16.0); 2025 generation 1,182.4 bn kWh (UES 1,166.5); installed capacity 270.3 GW on 2026-01-01. HTML text in Russian, no API, no table; monthly consumption releases not found (the press-release listing URL returned 404). An hourly page exists: `https://www.so-ups.ru/functioning/ees/ees-indicators/ees-gen-consump-hour/` (not examined for data feeds).
- **cadence:** annual page (plus press releases, not verified); **lag:** 2025 total available in Jan-Feb 2026; **history start:** not confirmed; **units:** bn kWh; **key needed:** no.
- **licence/terms:** terms not found (the "Использование информации" page holds only a cookie notice). **badge:** B for weights (official annual). Better than Ember for weights? It is the operator's own figure and current, but Ember is machine-readable; use SO UPS as the cross-check and to state which definition Ember follows.
- **fixture:** `so_ups_energy_system_2025_extract.txt`.

## Russia proposal
- Household: Rosstat per-100-kWh series **if the owner accepts pinning the Russian Trusted CA for rosstat.gov.ru only**; otherwise "no source". Industrial: "no source". Wholesale: "no source" (ATS unreachable). Mix/demand: Ember plus SO UPS cross-check. Badge C.

---
- **date checked:** 2026-09-29.
