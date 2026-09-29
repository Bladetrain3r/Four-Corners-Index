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
result: green after 2 red rounds inside R2 — checks/verify_fixtures.py: 11 dirs, 0 problems; 5 agent drafts assembled into SOURCES.md; tests/test_sources_doc.py went red twice on real gaps (fixtures/china and /southafrica cited only by brace shorthand; 11 entries with no per-entry check date and 4 with no licence line; ZA-3 had no licence line because nothing was fetched) and green after the doc was fixed (17 passed, ruff clean)
decision: proceed to STOP-1 — every region/layer cell is mapped or "no source" with a reason; a US wholesale follow-up (added mid-round at Ziggy's "expand sources as we find them") found no reusable US series

### R3 — G1/fixtures hygiene — 2026-09-29T19:50Z
plan: before committing agent-fetched fixtures, verify each dir with checks/verify_fixtures.py and independently grep for the EIA key | eval: verifier + `grep -rlF "$EIA_API_KEY"` | expect: 0 problems, 0 matches
result: red then green — verifier crashed with a traceback on a manifest wrapped in an object (EIA, Ember), which is a bug in my checker, fixed and tested (12 tests); EIA/Ember manifests then flattened to lists; Eurostat manifests lacked source_kind; key grep 0 matches throughout. NYISO and MISO data fixtures were fetched by the US-wholesale agent and deliberately deleted before commit (NYISO grants no reuse licence; MISO terms unreadable), licence notes kept
decision: proceed — 11 fixture dirs committed in six commits, each only after it passed the verifier

### G1 retrospective
Rounds used: 3 (R2 with two internal reds, R3 with one, plus the R1 setup). What the evaluation caught that reading would not: the doc test found 11 entries with no per-entry date and one fixture dir cited only by shorthand, which five careful drafts and my own read-through missed; the verifier crash exposed that agents had used a different manifest shape than the one I specified; the key-grep proved the EIA key was in none of ~100 fixture files rather than trusting the agent's report. What I would specify differently: give delegated agents the exact manifest schema as a file to validate against before they report (I gave prose; two of five deviated), and give the STOP-1 checklist items as an answer template so the source map, bands and weights come back in one shape. The largest finding was structural, not technical: the Wholesale index is EU-only and China is 55.3% of a headline resting on the weakest data. GATES should have asked at G0 whether an index with one contributing region should exist at all.
Environment notes: five parallel research agents each ran about 5 to 19 minutes (from the agent run records) in one wall-clock window; serial time was not measured. Each reported "nothing committed", so committing stayed a serial step of mine; the stop-hook complained about untracked files four times while agents were still writing, and I committed only verified directories each time.
