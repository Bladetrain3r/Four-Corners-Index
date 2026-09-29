# BLOCKED — G3 (cross-checks) — 2026-09-29

**Why I stopped.** G3 has three red rows that come from real behaviour in the publishers' data, and none of them can be fixed by changing my code. The rules (GATES.md) say a check may be tightened by the builder and never loosened without Ziggy's word, so I did not touch them. This is the first round on each, not the third; I am stopping early because no new idea of mine changes the outcome. Nothing past G3 has been started.

Evidence: `evidence/G3.md` (run 2), `evidence/G3-run1-red.md` (run 1, unedited), `checks/tolerances.yaml` (committed before any check ran, `85d3655`).

## What is green
55 of 58 fixture rows, including every gate-level requirement: Eurostat household all-taxes and excluding-taxes EU-27 against the publisher's article (8 of 8 exact to four decimals) and non-household band IC (4 of 4 exact); EIA US residential and industrial against Electric Power Monthly Table 5.6.A (4 of 4 exact) and Henry Hub monthly against the mean of daily; Ember monthly price against the mean of daily for six countries; ECB monthly against the mean of daily (exact); Ember US generation, Russia demand and China demand against independent figures. One check (`eurostat_nonhousehold_...`) was red in run 1 because my premise was wrong (see G3.md); fixed with the tolerance unchanged.

## The three open items and what I recommend

**B. Ember yearly vs monthly Demand** (my own extra check; the gate's Ember requirement is met by the price check).
Ember's monthly and yearly files disagree for every area but the US: EU -6.1%, ZA -6.0%, RU -2.4%, CN -1.1%; total generation shows the same gaps, so it is coverage, not a definition. Recommend: keep the comparison as a **non-gating information row** with the numbers above, and add a method rule (in `METHOD.md` at G4): *weights use Ember's yearly Demand; monthly Ember series are used only for shares and intensity, never mixed with yearly levels.* Alternative: keep it red and make it a permanent known failure (worse: a check nobody can pass).

**C. World Bank vs IMF, Europe gas** (my own extra check; the gate needs only a spot comparison).
34 of 36 months within 2%, median 0.64%; only 2023-10 (8.8%) and 2023-11 (5.7%) exceed 5%. Recommend: gate on the **latest 12 months within 5%** (worst is 1.9%) and keep the 36-month sweep as an information row that names the two months. Alternatives: widen to 10% for all months; or drop the sweep. I chose the 12-month window after seeing which months diverge, so it is post hoc; say so if you prefer the wider tolerance instead.

**D. Sanity range on Eurostat household prices** (live histories only; CI passes because the fixtures do not span that period).
The Netherlands 2022-S1 is published at 0.0336 EUR/kWh all taxes and 0.0278 excluding VAT, under my 0.03 bound. The value is Eurostat's, not a unit error. Recommend: bound **all-taxes (`I_TAX`) at 0.03** as now and give the two lower tax levels their own bound of **0.01**, with this value named as the reason. Alternative: lower the single bound to 0.02.

## If you say "approve the recommendations"
Next session: amend `tolerances.yaml` and the three rows in `checks/cross_check.py` (one commit, message names this report), re-run, remove the two `xfail` marks in `tests/test_cross_check.py`, write the G3 retrospective, then start G4. About half an hour of work. If you prefer an alternative, say which.

## Also for your attention (not blocking)
1. **Industrial band.** Eurostat's own EU non-household headline is band **IC** (500-1,999 MWh/yr), not ID (2,000-19,999) that we chose. Recommend keeping ID as the headline (your "typical mid-size band") and adding IC as a highlighted comparison series so both are shown.
2. **Ember Demand follows inland demand**, not final consumption (4.1% above Eurostat's inland demand). Weights are unaffected; METHOD will say so.
3. **G1 hygiene fix (R10 in LOG.md):** I removed raw third-party data files for sources we do not use whose terms restrict reuse or state none (Bank of Russia XML, Chinese government PDFs, Eskom extracts). They remain in git history; I cannot rewrite history. Say if that matters to you.
4. **Research passes queued at STOP-1 answers**, both done and not adopted: Russia secondary sources (none usable: only a discontinued modelled World Bank series, licence unconfirmed) and alternate regions (Brazil, Türkiye and the United Kingdom are the workable candidates; findings are the agent's, unverified by me).
