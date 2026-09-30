# STOP-3: the site and the live pipeline (G5, G6)

*2026-09-30. Evidence: `evidence/G5.md`, `evidence/G6.md`, screenshots in `evidence/G5/`. Nothing is switched on: merging, Pages, the first real dispatch and any announcement are yours.*

## The short version
- **The dashboard is built** (static HTML, CSS and JS, no third-party code, no request to any host but its own): overview with both indices, region pages, indices page (weights, variants, contributions, wholesale composition, revision ledger), method, sources, downloads. It works at 390 px, in light and dark, and by keyboard.
- **The pipeline is ready to run**: `daily.yml` (fetch each source separately, keep what changed, rebuild, record source health, commit, open an issue naming a failing source, redeploy) and `pages.yml`. All 19 requests fetched and parsed live from here in a dry run.
- **220 tests pass**, CI is green on the branch head, ruff is clean, repo 21.5 MB, generated site 13 MB.
- **What is unproved**: everything that needs GitHub itself (list at the end). Nothing was run on a runner.

## What goes live when you switch it on
| | Latest month | Status | Level | Index (2015 = 100) |
|---|---|---|---|---|
| Retail (EU, US, China, UK; Russia has no price) | 2026-08 | **provisional** | 0.157 USD/kWh | 112.6 |
| Wholesale (EU only) | 2026-08 | final | 0.150 USD/kWh | 346.0 |

Variants beside the headline: equal-weighted 0.253 (145.8), excluding China 0.248 (143.7). Ledger: 420 lines, hash-chained, verifier passes; the site has a currency toggle (USD, EUR, ZAR) and a retail weighting toggle.

## What is provisional
- **Retail: 12 of 140 months** (2025-09 to 2026-08): the EU and UK household prices are carried forward from 2025-S2 (published half-yearly, about nine months late) and the US EIA values are preliminary until they are 12 months old (my assumption; EIA's revision window is not confirmed). **Wholesale: none.**
- China is one Shanghai tariff (0.617 CNY/kWh, badge C, low confidence, currency and re-issue not confirmed): 58.9% of the weighted index moves only with CNY/USD. The excluding-China variant is on the headline page for that reason.

## Known gaps by region (each is shown on the site as "no source" with its reason)
- **EU**: household, industrial, wholesale all present (household and industrial half-yearly, carried).
- **US**: household and industrial (EIA, preliminary); wholesale no source (only CAISO and ERCOT publish reusable history).
- **China**: household only; industrial and wholesale no source.
- **UK**: household and industrial (DESNZ, in the index for household); wholesale out (Ember does not say whether it converts from sterling).
- **Russia**: no price source at all (Rosstat chain not trusted from the build environment; Bank of Russia terms restrict reuse); generation mix only. In the weights, not in the prices.
- **South Africa**: beside the basket, generation mix only (Eskom terms bar reuse).
- Drivers: gas, coal and FX are shown; the EU carbon price and RUB are shown as no source.

## Decisions and questions for you
1. **Merge PR #1** (it holds G0 to G6). The workflows do nothing until they are on `main`.
2. **Switch Pages on** (Settings > Pages > Source: GitHub Actions), then run `pages` once by hand. Going public and any announcement are yours.
3. **Settings only you can change** (I did not touch them): Actions > General > Workflow permissions (the daily job needs `contents: write` and `issues: write` from `GITHUB_TOKEN`; the file requests them, an org or repository policy may refuse); branch protection on `main` (a bot push of `data/` and `ledger/` needs an allowed path); the `EIA_API_KEY` Actions secret (name in `reports/SETUP.md`).
4. **First dispatch, in this order:** run `daily` once with the `force_fail` input set to `eia` (proves the red run, the issue and the banner on the real thing), close that issue, then run it clean. Say if you would rather I not have a bot commit to `main` daily (see 5).
5. **A deviation to accept or overrule:** the daily job commits `data/health.json` each day (the last good date changes daily), which is a small break with "an unchanged source produces no commit". Source data still commits only when it changes. The alternative loses the last good date.
6. **Raw snapshots:** the daily job packs new snapshots as a monthly Release asset (`raw-YYYY-MM`) and restores from them; the archive in git holds the launch set. Untested against a real Release.

## Cost and iteration summary (from `LOG.md`)
- 23 rounds (R0 to R22), 6 gates plus G3b, G4b and G4c, 2 STOP points before this one, 44 commits, 220 tests.
- Reds found by an evaluation rather than by reading: about 28 recorded in the log across the gates; the pattern is in the retrospectives: layout and data-shape defects (one broken region page out of six, a hidden table, a missing legend) were caught only by rendering every page; source-behaviour surprises (Eurostat bands, Ember monthly versus yearly, the UK's last semester) only by comparing sources; non-determinism (the archive, the build info) only by running twice.
- **Money and tokens: not measured.** I cannot see this session's cost meter; the figure would have to come from your billing. No paid service was used other than this session; the only key used is your free EIA key.

## What I would do next
1. After the first dispatches, fix whatever the runners show (the likely ones: source reachability from GitHub's IPs, token permissions, the Release upload).
2. Confirm the open source questions: EIA's revision window, the Shanghai tariff (is it still current, and in CNY), Ember's UK currency (ask Ember or Elexon), then a method version if any of them changes a number.
3. Candidates you noted: an air-quality layer instead of carbon; alternative regions with public cost data (Brazil, Türkiye); more Chinese provinces if terms allow; a nowcast for the EU household lag (deferred in METHOD section 9).
4. Add the browser tests to CI (Playwright is preinstalled here, not on the runner; a job that installs it would close the gap that CI cannot see a rendering regression).

## Not proved (needs GitHub, so it waits for the merge)
The cron trigger and the dispatch input; the secret reaching the run; runners reaching all six sources; `GITHUB_TOKEN` pushing to `main`; Release create, upload and restore through `gh`; issue creation and duplicate search; the reusable-workflow call from `daily.yml` to `pages.yml` and the Pages deploy. Details in `evidence/G6.md`.
