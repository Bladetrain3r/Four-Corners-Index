# BLOCKED — G3b (UK cross-checks) — 2026-09-30

**Why I stopped on the UK.** Two rows of the UK cross-check are red for a real reason that no change of mine fixes, and I do not loosen a check without Ziggy's word. Everything else went ahead (the ex-China variant, the snapshot archive), because none of it needs the UK numbers. Tolerances (`checks/tolerances.yaml`) were committed before the UK check was run (`64a189f`); the runner is `checks/cross_check.py::uk_checks`.

## What was compared
DESNZ QEP 5.6.2 (household, Medium, 2,500-4,999 kWh) and 5.4.2 (non-household, Medium, 2,000-19,999 MWh), United Kingdom column, incl. and excl. tax, against **Eurostat's own UK series in national currency** (the UK stopped reporting after 2020-S1): 11 semesters, 2015-S1 to 2020-S1, 44 rows, tolerance 0.0001 GBP/kWh (0.01 penny), written in advance. My tax-level mapping was also stated in advance and turned out right: household incl. tax = `I_TAX`, excl. tax = `X_TAX`; non-household incl. tax (taxes and levies but not VAT) = `X_VAT`, excl. tax = `X_TAX`.

## Result: 42 of 44 rows pass
- **Household incl. tax (the series the Retail index would use): 11 of 11 pass, including 2020-S1** (0.1927 both).
- Two rows fail, **both in 2020-S1, the last semester Eurostat ever held for the UK**:

| series | DESNZ | Eurostat | difference |
|---|---|---|---|
| household excl. tax vs `X_TAX`, 2020-S1 | 0.133338 | 0.1340 | 0.0007 |
| non-household incl. tax vs `X_VAT`, 2020-S1 | 0.134153 | 0.1331 | 0.0010 |

In the same semester the other two comparisons (household incl. tax; non-household excl. tax) match exactly. There are no "revised" markers on those cells in DESNZ's file, so I cannot blame a later revision. It looks like the two publishers split taxes differently for Eurostat's final UK submission, but that is a reading, not something I have shown.

## Recommendation
Keep the tolerance (0.0001) and gate on the ten semesters 2015-S1 to 2019-S2 (40 rows), and report 2020-S1 as an **information row** with the two differences above. The practical effect on the index is nil: the used series matches in all eleven semesters. Alternatives: widen the tolerance to 0.0011 for 2020-S1 only; or keep them red and never use the UK's industrial and excl.-tax series. **The choice of 2020-S1 is post hoc**, made after seeing which rows failed; say if you would rather widen than re-scope.

## What this blocks
Only the UK's entry to the Retail index as a weight-bearing region (METHOD v3, headline method 2). Until you answer, the UK adapters exist and their series are published on the regional pages' data files, but the UK is not in any index. CI stays green through strict xfail on the two checks (`tests/test_cross_check.py`).

## Separately: the UK wholesale price stays out regardless
Ember's price page says only that hourly data comes from "EMR (UK)" and does not say whether the UK price is converted from sterling to euro; I have no independent UK wholesale figure to test it against. Not confident enough to put it in an index. If you can confirm the currency treatment with Ember, or point me to an open UK day-ahead source (for example Elexon), I will add it.
