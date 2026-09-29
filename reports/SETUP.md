# Setup before the first cloud session (Ziggy's hands)

1. **Push** this repo to `origin` (`git push -u origin main`).
2. **Visibility and licence:** decided 2026-09-29: public, MIT (`LICENSE`). Pages is switched on at STOP-3.
   GitHub Sponsors: live 2026-09-29; `.github/FUNDING.yml` is in; the footer link comes at G5.
3. **EIA API key** (free, instant registration at eia.gov/opendata). Put it in two places:
   - the repo's Actions secrets as `EIA_API_KEY`;
   - the cloud environment's environment variables as `EIA_API_KEY`.
   ENTSO-E is optional (an emailed request, up to 3 working days); if you do it, use the name `ENTSOE_TOKEN`.
4. **Cloud environment network access:** the session fetches from the data sources, so the default package-registry-only
   access is not enough. Allow at least these domains (or full access, if you prefer):
   `ec.europa.eu`, `api.eia.gov`, `www.eia.gov`, `ember-energy.org`, `files.ember-energy.org`,
   `data-api.ecb.europa.eu`, `www.cbr.ru`, `rosstat.gov.ru`, `www.worldbank.org`, `thedocs.worldbank.org`,
   `www.eskom.co.za`, `www.nersa.org.za`, `www.stats.gov.cn`, `www.ndrc.gov.cn`, `www.so-ups.ru`, `www.atsenergo.ru`,
   and `web-api.tp.entsoe.eu` if you get the token.
   G1 adds any domain it finds missing to its STOP-1 report rather than working around it.
5. **Start the session** on this repo with the kickoff prompt below.

## Kickoff prompt
> Read CLAUDE.md, then SPEC.md, GATES.md, SOURCES.md and LOG.md. Work the gates in order, starting at G0, using the loop in CLAUDE.md, and log every round in LOG.md. Stop at STOP-1 and write reports/STOP-1.md as GATES.md describes; open a PR to main linking it; then stop.

## After each STOP
Answer in the report file (a commit) or in a PR comment, then start the next session with:
> Read CLAUDE.md and the latest report in reports/ with my answers, then continue from the next gate.
