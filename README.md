# Four Corners Index

What electricity actually costs across the EU, the US, China and Russia, with South Africa beside them:
retail, industrial and wholesale prices, the generation mix behind them, and the drivers that move them. Two
monthly indices (Retail and Wholesale), consumption-weighted, in nominal USD per kWh, each re-derivable from its
kept sources.

Status (2026-09-30): both indices are built from 2015-01 and reproducible offline (G0 to G4 done; the dashboard and daily pipeline are next). Not live.

![Retail and wholesale indices](evidence/G4/index_chart.png)

- `SPEC.md`: what is built and why
- `GATES.md`: the build order and each gate's pass/fail
- `CLAUDE.md`: the working card for the building session
- `SOURCES.md`: the data sources (desk research; re-verified at G1)
- `LOG.md`: the build log, one block per iterate-evaluate-decide round
- `METHOD.md`: the frozen index method; `reports/`: the STOP reports; `evidence/`: one file per gate
- `data/index/`, `ledger/index.jsonl`: the published numbers and their hash-chained ledger (`python ledger/verify.py`)

Not a coin, not a forecast, not advice.
