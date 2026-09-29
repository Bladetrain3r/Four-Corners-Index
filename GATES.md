# Gates

*Fixed before any code (2026-09-29). A gate passes only when every check is green and its evidence file exists
under `evidence/`. The builder never works past a red gate. A gate's checks may be tightened by the builder (logged
in `LOG.md`), never loosened without Ziggy's word. **STOP** means stop the session, write the report named, and wait.*

## G0 — Scaffold
- Repo layout per `CLAUDE.md`; `pytest` runs; CI (GitHub Actions) runs lint and tests on every push and PR.
- A repo size check in CI: fails above 200 MB tracked.
- Evidence: `evidence/G0.md` (tree, the CI run URL or the local equivalent output).

## G1 — Sources verified
- `SOURCES.md` has one entry per source actually used. Each entry gives the dataset or series code, the endpoint, cadence,
  lag, history start, units, key needed (yes or no), the licence with the quoted reuse sentence and a link, known breaking
  changes, and a date checked.
- For each keyless source: one real response saved as a fixture (`fixtures/<source>/`, small; trimmed if large) with
  its fetch date and URL. For each keyed source: a fixture from the provider's published sample or documentation, marked as
  such, until the key exists.
- Each region/layer cell in the SPEC's region table is mapped to a source or marked "no source" with the reason.
- The desk research in `SOURCES.md` (2026-09-29) is a starting point, not evidence: re-verify every line.
- Evidence: `evidence/G1.md`.
- **STOP-1.** Report `reports/STOP-1.md`, covering: the source map; per region, which series is "household" and "industrial" (band
  choices); the consumption source for weights; the carbon price in or out; the China and Russia plan with its caveats; the
  keys needed. (The code licence is settled: MIT.) Ziggy answers in the repo (an issue or a commit to the report) before G2.

## G2 — Adapters
- One adapter per source: fetch (live, or fixture when offline or keyless) → a normalised series in the common schema
  (`schema/series.schema.json`: source, series_id, region, layer, buyer_type or fuel, period start/end, value,
  unit, currency, as_of, retrieved_at, raw_sha256).
- Tests per adapter against its fixtures: parse succeeds, the schema validates, units are right, no silent NaN, and a
  deliberately corrupted fixture (a changed column or tag name) fails loudly with the source named.
- Evidence: `evidence/G2.md` (the test output).

## G3 — Cross-checks (the external oracle)
- For each A-badge source, at least one check of our normalised numbers against a figure the publisher itself states
  elsewhere (for example our EU-27 average against Eurostat's published EU-27 value; the US national average against
  EIA's stated national figure; a zone's monthly average against the provider's own monthly figure). Tolerances are
  written in `checks/tolerances.yaml` **before** the check is run, and the commit order shows it.
- B and C sources: a sanity range and a spot comparison against one independent published figure, documented.
- Evidence: `evidence/G3.md` (table: check, ours, theirs, tolerance, pass).

## G4 — Index
- `METHOD.md` written from the SPEC outline and **committed before any index value is computed** (the commit order
  shows it). The nowcast decision is recorded there.
- The monthly backfill from 2015-01 for both indices, the equal-weighted variant, and weights by year.
- **Reproducibility:** a clean rebuild from the raw snapshots (no network) produces byte-identical outputs (hashes compared).
- **Continuity:** every month-on-month move above a threshold stated in METHOD.md has an explanation line in
  `checks/explained_moves.md` (source event, crisis, tariff date, FX), or it is a defect.
- The ledger (`ledger/index.jsonl`) is hash-chained; a verifier script passes; tampering with one line makes it fail (tested).
- Evidence: `evidence/G4.md`.
- **STOP-2.** Report `reports/STOP-2.md`: the backfilled series (a chart image), the weights, notable moves and their
  explanations, the open method questions. Ziggy answers before G5.

## G5 — Dashboard
- Static site per the SPEC's visible metrics; it builds from the JSON outputs only.
- Tests: every headline tile shows a value, an as-of date, a source and a badge; a gap renders as a gap with its reason;
  the toggles (USD/EUR/ZAR, equal-weighted) change what they claim to; downloads link to files that exist.
- Headless browser smoke tests (Playwright or equivalent) at desktop and 390 px width, with screenshots committed to
  `evidence/G5/`; no horizontal scroll at phone width; no request to any host but the site and the pinned chart CDN
  (or the chart library vendored).
- Basic accessibility: contrast, labels on charts, keyboard reachable.
- Evidence: `evidence/G5.md`.

## G6 — Live pipeline
- The scheduled daily workflow and the Pages deploy workflow exist, their YAML validates, and their entrypoints pass when run
  locally the way the workflow runs them. A real dispatch needs the workflows on the default branch, so the first real
  dispatch happens after Ziggy merges at STOP-3; say which steps that leaves unproved.
- Failure path proved: a forced source failure (a test flag) turns the run red and opens (or would open, in a dry run) an
  issue naming the source; the site shows the last good date for it.
- A **simulated 15th-of-month publication** (a dry-run flag) appends one ledger line, publishes provisional values, and
  the verifier passes.
- Evidence: `evidence/G6.md`.
- **STOP-3 (the stop rule).** Report `reports/STOP-3.md`: what is live or ready to go live, what is provisional,
  known gaps by region, the cost and iteration summary from `LOG.md`, and what the next session would do. Going
  public (Pages on, repo public, announcement) is Ziggy's act, never the builder's.

## Iteration limits
- A gate that fails the same check three rounds in a row: stop, write `reports/BLOCKED-<gate>.md` (what was
  tried, what the evidence says, the options), and wait.
- A source that cannot be reached or licensed: never scrape around a block or a terms-of-use limit; record
  "no source" and move on.
