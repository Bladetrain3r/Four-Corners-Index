# G7b evidence: Eskom figures on the South Africa card (2026-10-01)

**Request:** Ziggy, 2026-10-01: "Add in Eskom data as well, what the hell, not like there's any actual income involved at this point lol." Earlier (STOP-1, 2026-09-29): "if there aren't any publicly licensed sources then let's play it safe. Can drop SA maybe."

## What the terms say (read 2026-09-29; clauses recorded verbatim in `data/manual/eskom_tariffs.json`)
- 2.1: licensed for "private, personal, educational and/or non-commercial purposes only". 2.2: no "commercial and non-private" use without written consent.
- 2.8: "Users may quote small and reasonable amounts of content ... subject to such a quote being placed in inverted commas and acknowledged."
- 2.10: no "web crawlers, robots or web spiders" to "search, collect or copy content ... for any purposes" without written consent. **This clause does not depend on income**, so the daily pipeline cannot fetch from Eskom whatever the reading of 2.1 and 2.2.

## What was done, and what was not
- Two figures **typed in by hand** as dated facts (read 2026-09-29), like the Shanghai tariff: Homelight 20A 2026/27, 270.30 c/kWh including VAT (235.04 excluding), shown as ZAR 2.7030 and marked low confidence (a prepaid low-usage tariff, not an average household; most households pay a municipal tariff); and the realised average price of "Industrial (Excl NPA)" customers, financial year 2025/26, 212.03 c/kWh (a realised average, not a tariff; VAT treatment not stated in the file, read as excluding).
- They are on the South Africa card only, in neither index. Wholesale stays "no source" (no market).
- **Not done:** no Eskom time series (that would be copying a dataset, not quoting; it needs Eskom's written consent), no automated collection, no Data Portal, and Eskom was not asked for consent. The sources page states all this, says the figures are removed if Eskom objects, and names the sponsor link next to the "no payment for the data" reading of clause 2.1.
- METHOD version 4 (additive, no index definition or value changes) replaces the sentence that said South Africa's price layers were "no source" and records the air tab and these figures as shown beside the indices.

## Evaluations run
- `tests/test_eskom.py` (5 tests): **no pipeline module, registry URL or workflow mentions Eskom** (the compliance guarantee, a test, not a promise); the two values are as read and the VAT arithmetic holds (235.04 x 1.15 = 270.30 to Eskom's rounding); the clauses are recorded verbatim and the sources entry says "never fetched automatically", quotes 2.8, states the removal on objection; the card has both figures with period, source link and caveat, wholesale a gap; METHOD v4 text present and the false sentence gone.
- Browser (`test_south_africa_shows_the_two_eskom_figures...`): both cards render with "tariff year 2026/27", "low confidence", the municipal caveat and the Eskom link; switching to rand shows the native figure; the sources page shows the entry and the "clause 2.10" not-used text. Screenshot seen at 390 px.
- The pinned launch reproduction still passes: `build_info.json` is excluded from the hash comparison (it records the method document version, 3 at launch, 4 now) and is checked separately: equal to the launch file except that one field.

## Not proved
- Whether Eskom would object: nobody has asked. Reading 2.1 as covering a public, unpaid-for-data site with a sponsor link is Ziggy's call, not a legal opinion.
- The committed `data/index/build_info.json` still says method version 3 until the next daily run regenerates it, so the footer reads "method version 3" for up to a day while the Method page says version 4.
