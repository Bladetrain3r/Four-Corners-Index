# Build log

*One block per round (format in `CLAUDE.md`), newest at the bottom, plus a retrospective per gate.*

### R0: prep, 2026-09-29 (conductor, local)
plan: write SPEC, GATES, CLAUDE card, desk-research SOURCES before any code | eval: Ziggy reads them before the first push | expect: his four decisions (two indices, consumption weights, South Africa beside, nominal) reflected verbatim
result: see the first commit
decision: proceed to G0 in the cloud session once keys and the environment are set

### R1 — G0/scaffold — 2026-09-29T19:05Z
plan: create the layout from CLAUDE.md, a tiny schema-validity test, ci.yml (ruff + pytest + 200 MB tracked-size check), pyproject | eval: `python3.12 -m pytest`, `ruff check`, `python3.12 checks/repo_size.py`, plus a test that the size check fails on an over-budget input | expect: all pass, size check demonstrably able to fail
result: red then green — first `ruff check` flagged PLW1510 (subprocess.run without check=) in tests/test_scaffold.py; fixed with check=False; rerun: ruff clean, 5 passed, size 0.06 MB of 200, size check exits 1 at a 0.0001 MB limit (tested)
decision: proceed — G0 checks are green locally; the CI run itself is proved on push (see evidence/G0.md)

Env note (R1): the default python3 is 3.11; the build uses python3.12 in `.venv` (CI pins 3.12). Dev-only deps: pytest, ruff, jsonschema, pyyaml. The pipeline itself stays stdlib.

### G0 retrospective
Rounds used: 1 (one red ruff flag inside it). What evaluation caught that reading would not: the lint rule PLW1510 firing on my test helper, which I would not have spotted by eye; and the size check's failure path was only proved by actually running it with a tiny limit. Next time: GATES should say which Python the local environment must use (the box default was 3.11, the spec says 3.12), and G0 could name the lint ruleset instead of leaving it to defaults.

### R2 — G1/sources — 2026-09-29T19:20Z
plan: re-verify every SOURCES.md line from this environment via 4 parallel research agents (EU+HICP+consumption; EIA+Ember; FX+World Bank+carbon; China+Russia+South Africa); each saves small fixtures under fixtures/<source>/ with fetch date + URL and drafts entries in the scratchpad; I assemble SOURCES.md | eval: a script (checks/verify_fixtures.py) that every fixture dir has a manifest with url + fetch date + sha256 matching the file, plus a table of region/layer cells each mapped to a source or "no source" | expect: every SPEC region cell mapped; every keyless source has a real fixture; the EIA fixture is keyed-live
result: pending
decision: pending
