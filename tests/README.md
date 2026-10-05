# Writing tests here: what the daily job does to your assumptions

The daily job rewrites `data/`, `ledger/index.jsonl` and `data/manifests/` every day, and the Pages job runs the tests on the freshly built
site before it deploys. A test that is true today and false tomorrow therefore **stops the site deploying** (it did on 2026-10-01 and 2026-10-03:
a ledger count and a gas price).

- **Never pin a value from `data/`, the committed ledger or the committed site to a literal** (a price, a date, a month, a count of lines or
  revisions). Pin it to the launch bundle instead: use the `launch_site` fixture (conftest) or `snapshots/launch/` (manifest, ledger, output
  hashes), which the daily job never touches.
- Tests of the committed data assert **relations and structure**: a card equals the newest point of its series, shares sum to one, the chain
  verifies, every later ledger line is a new month or a same-month revision, a month is never published in its own month.
- Ask of every assertion: "what does the daily job do to this tomorrow, on the 15th, and in January?"
- Anything that needs the network or a token is not a CI test here.
