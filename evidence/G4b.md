# G4b evidence — 2026-09-30 — Ziggy's STOP-2 answers: ex-China variant, snapshot archive, UK

## Ziggy's answers (in the session, 2026-09-30) and what was done
| Answer | Done |
|---|---|
| "add the ex-china variant" | METHOD v2 (committed first, `git log -- METHOD.md`), variant columns in `data/index/retail.csv`, chart line, tests. Not a ledger series. |
| "bringing the UK in as a weight bearing index if you're confident in the sources" | Adapters, fixtures and checks built. Confident for household, **not** for UK wholesale. UK entry to the index waits on `reports/BLOCKED-G3b.md` (two 2020-S1 rows). |
| "github can handle one 8MB archive binary, we'll commit it once" | `snapshots/raw_2026-09-29.tar.gz` (8.45 MB, 21 snapshot files, deterministic), with `python -m pipeline.snapshot --restore`. |
| "don't see a need to override any [assumption]" | Unchanged: EIA provisional window 12 months, EU carry-forward, no Industrial index. |

## 1. Ex-China variant
Defined in METHOD.md section 4 (v2) before it was computed. Retail excluding China, EU + US only, 2015 = 100: 100.595 (2015-01) to **142.661** (2026-08), against the headline's 111.730 and the equal-weighted 133.815. Level 0.241059 USD/kWh against the headline's 0.152973 (2026-08). Independent recomputation of **every** month from `weights.csv` and `region_prices.csv` agrees to 1e-6 (`tests/test_index_outputs.py::test_retail_excluding_china_is_recomputed_independently_for_every_month`); 2026-06 by hand: 0.240419 both ways. The largest month-on-month move of the variant is +4.28% (2021-07); the variant is not a headline index, so the METHOD.md continuity threshold does not apply to it.
The headline is unchanged: rebuilding against the new snapshots appended **0** ledger lines (`build_info.json`: `ledger_lines_added: 0`; all 280 lines still `method_version` 1).

## 2. Snapshot archive
```
8446303 bytes  raw_2026-09-29.tar.gz
55c46e22b63dd7f3f141f37d46ae9efd1f86113ed89b1dee912527bd427e1c32
```
Deterministic (the gzip header no longer embeds the output file name: the first version produced different bytes from different paths; found by archiving twice). `tests/test_snapshot.py`: same bytes from any path; restore reproduces every file and checks each SHA-256; a tampered snapshot is refused at archive time; a modified, unlisted or missing member is rejected at restore. Proof it works end to end, with the network blocked:
```
restored 21 files into /home/user/Four-Corners-Index/raw_cache, all matching the manifest
files per rebuild: 118; network connections attempted: 0 (any attempt raises)
rebuild 1 == rebuild 2 (all 118 files byte-identical): True
rebuild == committed outputs: True
```
`tests/test_reproduce.py` now restores the committed archive into a temp directory and rebuilds from it, so the reproducibility proof runs in CI as well as locally.

## 3. UK (G2b, G3b)
- Adapter `pipeline/desnz.py` (tables 5.6.2 household, 5.4.2 non-household, UK column, band definition and unit verified on every parse; only the 2015 methodology kept). The real workbooks were parsed live: 5.6.2 gives 44 points (15.56 p/kWh in 2015-S1 to 29.777 p in 2025-S2), 5.4.2 gives 43. Shared stdlib xlsx reader moved to `pipeline/xlsx.py`; ECB adapter and registry carry GBP; Ember maps United Kingdom to GB.
- URL discovery through the GOV.UK content API by attachment title (the file id changes every release; tested, including the "Domestic" versus "Non-domestic" prefix trap).
- G3b: tolerances committed first (`64a189f`). **42 of 44 comparisons with Eurostat's own UK series pass to four decimals**; household incl. tax (the series the index would use) 11 of 11. Two 2020-S1 rows open: `reports/BLOCKED-G3b.md` (recommendation and alternatives). Strict xfail in CI.

## 4. Cross-check summary (live mode)
```
99 of 101 gating rows passed; 6 information rows
```

## 5. Tests, lint, size
```
............                                                             [100%]
154 passed, 2 xfailed in 16.54s
All checks passed!
tracked 6.69 MB, limit 200 MB: OK
13 fixture dirs checked, 0 problems
index.jsonl: 280 lines, 0 problems, chain intact
```
