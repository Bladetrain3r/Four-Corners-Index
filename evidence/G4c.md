# G4c evidence — 2026-09-30 — the UK joins the Retail index (METHOD v3)

Order of events (git log shows it): G3b amendment (`816c40f`, Ziggy's word) → **METHOD v3 (`b7bcae4`), committed before any value that includes the UK** → build with `--published 2026-09-30` → this evidence.

## What changed
- Retail composition: EU, US, China, **United Kingdom** (Russia still has no price). Weights (Ember yearly Demand of the previous year among the five basket regions): 2015 EU 19.9%, US 29.3%, CN 40.8%, RU 7.5%, **GB 2.5%**; 2026 EU 14.4%, US 23.5%, CN 54.4%, RU 6.1%, **GB 1.6%**. Renormalised over the four priced regions the UK is 2.7% (2015) and 1.7% (2026).
- Retail (2015 = 100): 100.644 (2015-01) to **112.576** (2026-08); level 0.157277 USD/kWh (was 0.152973 before the UK). Ex-China (EU, US, UK): **143.670**. Equal-weighted: 145.819 (was 133.8): with the UK at a quarter of the weight, the equal-weighted line follows the UK's 2022-23 household price spike (it peaks near 0.30 USD/kWh); that is the data, and the reason the weighted headline exists.
- Wholesale: unchanged (EU only; UK wholesale stays out, currency treatment unconfirmed).

## Ledger: a revision, not a rewrite
```
index.jsonl: 420 lines, 0 problems, chain intact
lines 420 = 280 version-1 lines (byte-identical to the ledger before this change: True) + 140 new lines
new lines: index ['retail'], method_version [2], published ['2026-09-30'], all supersede a version-1 line: True
```
The wholesale ledger lines were not touched (their `method_version` stays 1; the per-index headline method version is why). A second build appends 0 lines (idempotent), and `build_info.json` no longer records run-specific facts (an earlier version did, so a rebuild could never match it: found by the reproducibility test).

## One month re-derived independently from the raw snapshots (2026-06)
Prices in USD/kWh: EU 0.333561 (0.2896 EUR carried from 2025-S2 x 1.1518), US 0.1834, China 0.091058, **UK 0.39709** (29.77727 pence, 2025-S2 carried, GBP to USD via the ECB cross rate). Renormalised weights EU 0.1532, US 0.2503, CN 0.5792, GB 0.0172. Independent level 0.156600 = file 0.156600 (difference 4e-7, rounding); ex-China 0.246821 = file.

## Reproducibility, tests
```
files per rebuild: 118; network connections attempted: 0 (any attempt raises)
rebuild 1 == rebuild 2 (all 118 files byte-identical): True
rebuild == committed outputs: True
.............                                                            [100%]
157 passed in 17.45s
97 of 97 gating rows passed; 10 information rows
explained_moves.md is up to date
0 moves unexplained by the held drivers
```
Chart: `evidence/G4/index_chart.png` (four-region contribution panel; the palette with the UK as slot 4 passes the validator, contrast WARN relieved by direct labels).
