# fixtures/eia

Manifest wrapper metadata, moved out of MANIFEST.json (which is a flat list).

- **source**: EIA API v2 and bulk manifest
- **checked**: 2026-09-29
- **key_handling**: EIA_API_KEY read from environment only; api_key=REDACTED in every recorded URL; responses do not echo the key (verified by grep -F).
