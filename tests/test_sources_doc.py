import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "SOURCES.md").read_text()

FIXTURE_DIRS = sorted(p.name for p in (ROOT / "fixtures").iterdir() if p.is_dir())


def test_every_fixture_dir_is_cited():
    for d in FIXTURE_DIRS:
        assert f"fixtures/{d}" in DOC, f"fixtures/{d} not referenced in SOURCES.md"


def test_region_map_covers_spec_regions_and_layers():
    head = DOC.split("## What verification changed")[0]
    for region in ("EU", "US", "China", "Russia", "South Africa"):
        assert re.search(rf"\*\*{region}\*\*", head), f"{region} missing from the region map"
    for col in ("Household", "Industrial", "Wholesale", "Mix and carbon", "Consumption"):
        assert col in head, f"{col} column missing"


def test_no_cell_is_silently_empty():
    rows = [r for r in DOC.split("\n") if r.startswith("| **")]
    assert len(rows) >= 5
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        assert all(cells), f"empty cell in: {r[:60]}"


def test_every_source_entry_has_licence_and_check_date():
    # entry headings: '## E1.', '## EIA-1.', '## EMBER-1.', '## ZA-1.', '## CN-1.', '## RU-1.', and lettered parts
    entries = re.split(r"\n(?=## (?:E\d|EIA-\d|EMBER-\d|ZA-\d|CN-\d|RU-\d|[A-D]\. ))", DOC)[1:]
    assert len(entries) >= 20
    for e in entries:
        title = e.split("\n", 1)[0]
        low = e.lower()
        assert "date checked" in low or "checked" in low, f"no check date: {title}"
        assert "licen" in low or "terms" in low, f"no licence/terms: {title}"


def test_no_secret_in_docs():
    for name in ("EIA_API_KEY", "ENTSOE_TOKEN"):
        v = os.environ.get(name)
        if v and len(v) > 8:
            for f in (ROOT / "SOURCES.md", ROOT / "LOG.md"):
                assert v not in f.read_text()
