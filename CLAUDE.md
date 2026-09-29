# Four Corners Index — the building session's card

You are building the Four Corners Index: a public electricity-price dashboard with two monthly indices. The
work runs as a long unattended cloud session; Ziggy (the owner) checks in at the STOP points. The conductor (Ziggy's
coordinating Claude seat) wrote this card, `SPEC.md` and `GATES.md` on 2026-09-29.

This build is also an experiment in **how** an unattended session works: iterate, evaluate, proceed. `LOG.md` is a
deliverable, as important as the code.

## Read at start, every session
1. This file, then `SPEC.md` (the what), then `GATES.md` (the order and the pass/fail).
2. `LOG.md` (the last rounds) and `reports/` (the latest STOP report and Ziggy's answers).
3. `git log --oneline -15`.

## The loop (one round)
1. **Plan:** the next unmet check in the current gate; write one line in `LOG.md` saying what you will change and how you
   will know it worked (the evaluation), *before* changing anything.
2. **Iterate:** the smallest change that could pass that check.
3. **Evaluate:** run the check (a test, a script, a comparison). The evaluation is a command with output, never a reading of
   your own code.
4. **Decide:** proceed (the check is green, commit), iterate (red, and you have a new idea: log why the last try failed),
   or stop (the third red in a row on the same check, or a STOP point). Log the decision.

`LOG.md` round format (one block per round, newest at the bottom):
```
### R<n> — <gate>/<check> — <UTC timestamp>
plan: <change> | eval: <command or check> | expect: <what green looks like>
result: <green|red> — <one line of evidence: numbers, test counts, the failing assertion>
decision: <proceed|iterate|stop> — <why, one line>
```
Once per gate, add a **gate retrospective** (3 to 5 lines): rounds used, what the evaluation caught that reading would
not have, what you would specify differently next time. Those lines are what the owner reads to improve the
process.

## Boundaries
- Work only in this repository. Commit often, with messages that name the gate (`G2: eurostat adapter parses nrg_pc_204`).
- Branches: work on the session's branch; at each STOP point, open (or update) one PR to `main` whose description
  links the STOP report. Never merge to `main` yourself; never force-push; never change repo settings, Pages, or secrets.
- **Secrets:** API keys come only from environment variables (`ENTSOE_TOKEN`, `EIA_API_KEY`, or as `SOURCES.md` names
  them). Never print, log, commit or echo a key; redact it from any error text. If a key is absent, use fixtures and say so.
- **Network:** fetch only from the sources in `SOURCES.md` and package registries. Respect each source's terms and rate
  limits; cache what you fetch; never scrape around a block, a login or a terms-of-use limit. If a source is
  unreachable from this environment, record it, use its fixture, and continue.
- Never invent a number. A figure you did not measure or fetch is "not measured" or "no source". Any value on the site
  traces to a raw snapshot and a source.
- Keep fixtures small (trim to what the tests need; note the trimming). Large raw data goes to Release assets per the
  SPEC, never into git.

## Layout (create at G0; adjust if a reason appears, and log it)
```
pipeline/          adapters (one module per source), normalise, index, ledger, publish
schema/            series.schema.json, index.schema.json
fixtures/<source>/ small saved responses with fetch date and URL
checks/            tolerances.yaml, explained_moves.md, cross-check scripts
ledger/            index.jsonl (hash-chained), verify.py
data/              normalised series (CSV/JSON) that the site reads; manifests of raw snapshots
site/              static dashboard (HTML/CSS/JS), reads data/
tests/             pytest
evidence/          one file per gate (G0.md ...), screenshots under evidence/G5/
reports/           STOP-1.md, STOP-2.md, STOP-3.md, BLOCKED-*.md
.github/workflows/ ci.yml, daily.yml, pages.yml
```

## Style
Python 3.12, standard library first, type hints, small modules (under 400 lines). One adapter never imports
another. Tests name the source and the check. Plain, dated prose in the docs; no marketing voice on the site: the
numbers, their age, their source.

## When a STOP point arrives
Write the report as `GATES.md` says. Open or update the PR. Then stop working: do not start the next gate on assumptions
about the answer.
