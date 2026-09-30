# Russia: no price source reachable and verifiable from this environment (checked 2026-09-29)

No household, industrial or wholesale electricity **price** series could be fetched with TLS verification on.
Nothing below was measured; every price figure for Russia is "not confirmed".

| Source | Request | Result (2026-09-29, UTC ~19:00-19:20) |
|---|---|---|
| Rosstat (rosstat.gov.ru) | `GET https://rosstat.gov.ru/statistics/price` | TLS fails: curl exit 60 "unable to get local issuer certificate". `openssl s_client -proxy ... -CAfile /root/.ccr/ca-bundle.crt` shows the server sends only the leaf `*.rosstat.gov.ru`, issued by "Russian Trusted Sub CA" (Ministry of Digital Development), a national CA that is in neither the system store nor the proxy bundle. Same for gks.ru. **Not bypassed**: no `-k`, and no extra trust anchor added (that is an owner decision, see below). The XLSX `sred_potreb_cen_08-2026.xlsx` named in the desk research was therefore not downloaded and its existence, size and series names are **not confirmed**. |
| ATS (atsenergo.ru, www.atsenergo.ru) | `GET https://www.atsenergo.ru/`, `.../results/rsv/indexes/indexes1/index.htm`, `https://atsenergo.ru/` (3 attempts each about 1 min apart) | Connection reset after 11-13 s (proxy log: `ws_closed_mid_exchange`, "tunnel closed"). Consistent with geo-blocking of non-Russian addresses or upstream refusal; cause not proven. Day-ahead index for price zones 1 and 2: **unreachable from this environment**. |
| Market Council (www.np-sr.ru) | `GET https://www.np-sr.ru/` | Proxy answered 502 to CONNECT (policy denial or upstream failure). Unreachable. |
| Fedstat / EMISS (fedstat.ru, www.fedstat.ru) | `GET https://www.fedstat.ru/` | HTTP 403 "Forbidden" with a request ID. Not worked around. |
| Minenergo (www.minenergo.gov.ru) | `HEAD https://www.minenergo.gov.ru/` | HTTP 200, but no price series looked for beyond the front page (not confirmed). |
| SO UPS (www.so-ups.ru) | `GET https://www.so-ups.ru/functioning/ups/ups2026/` | Reachable (200). Gives annual generation and consumption only (fixture `so_ups_energy_system_2025_extract.txt`). No prices. |
| data.gov.ru | `GET https://data.gov.ru/` | Reachable (200) but a JavaScript app; no dataset for electricity prices looked up (not confirmed). |

## What the owner needs to decide
1. **Rosstat**: to read the XLSX in CI, the pipeline would have to trust the Russian Trusted Root/Sub CA for that one host (`rosstat.gov.ru`) only, obtained and fingerprint-checked out of band. This session did not do it. Alternative: ask Rosstat/Minenergo for a mirror, or accept "no source" for Russian household prices.
2. **ATS**: whitelist request is pointless if the block is geographic; GitHub Actions runners are also non-Russian. Treat Russian wholesale as "no source" unless a reachable mirror is found.
3. Hosts to whitelist for the proxy if an attempt is wanted: rosstat.gov.ru, atsenergo.ru, np-sr.ru (only if the block is a proxy policy rather than the upstream site).

What was tried instead: search-engine discovery of an alternative mirror of the ATS or Rosstat series (none found), SO UPS pages (annual consumption only), data.gov.ru (JS app only).
