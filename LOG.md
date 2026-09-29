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
