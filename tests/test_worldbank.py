import io
import zipfile

import pytest

from pipeline import worldbank
from pipeline.common import SourceError, dumps

CSV = "pink_sheet_monthly_gas_coal_last36.csv"


def _one(points, **want):
    hits = [p for p in points if all(p.get(k) == v for k, v in want.items())]
    assert len(hits) == 1, f"{len(hits)} matches for {want}"
    return hits[0]


def test_worldbank_pink_sheet_latest_values_and_units(fixture_bytes, series_schema):
    raw, m = fixture_bytes("worldbank", CSV)
    pts = worldbank.parse_csv_extract(raw, m["fetched_at"])
    for p in pts:
        series_schema.validate(p)
    ttf = _one(pts, series_id="worldbank:pink_sheet:natural_gas_europe", period_start="2026-08-01")
    assert ttf["value"] == 21.11 and ttf["unit"] == "USD/MMBtu" and ttf["region"] == "EU"
    assert ttf["period_end"] == "2026-08-31" and ttf["as_of"] == "2026-09-02" and ttf["currency"] == "USD"
    assert _one(pts, series_id="worldbank:pink_sheet:natural_gas_us", period_start="2026-08-01")["value"] == 2.77
    zac = _one(pts, series_id="worldbank:pink_sheet:coal_south_africa", period_start="2026-08-01")
    assert zac["value"] == 96.8 and zac["unit"] == "USD/t" and zac["fuel"] == "coal"
    assert _one(pts, series_id="worldbank:pink_sheet:coal_australia", period_start="2026-08-01")["value"] == 135.2


def test_worldbank_footnote_marks_stripped_and_36_months(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    pts = worldbank.parse_csv_extract(raw, m["fetched_at"])
    za = [p for p in pts if p["series_id"].endswith("coal_south_africa")]
    assert len(za) == 36 and za[0]["period_start"] == "2023-09-01"


def test_worldbank_lng_last_two_months_flagged_as_estimates(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    pts = worldbank.parse_csv_extract(raw, m["fetched_at"])
    lng = [p for p in pts if p["series_id"].endswith("lng_japan")]
    assert [p.get("source_flag") for p in lng[-3:]] == [None, "estimate", "estimate"]
    assert not any(p.get("source_flag") for p in pts if not p["series_id"].endswith("lng_japan"))


def test_worldbank_gap_marker_is_a_gap_not_a_number(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    edited = raw.replace(b"2026M08,135.2,96.8,2.77,21.11,13.94", b"2026M08,\xe2\x80\xa6,96.8,2.77,21.11,13.94")
    assert edited != raw
    pts = worldbank.parse_csv_extract(edited, m["fetched_at"])
    assert not [p for p in pts if p["series_id"].endswith("coal_australia") and p["period_start"] == "2026-08-01"]
    assert _one(pts, series_id="worldbank:pink_sheet:coal_south_africa", period_start="2026-08-01")["value"] == 96.8


def _xlsx(grid, sheet="Monthly Prices"):
    """A minimal real XLSX (zip of XML parts) built from a grid: shared strings for text, plain numbers."""
    strings: list[str] = []
    rows = []
    for r, cells in enumerate(grid, start=1):
        cs = []
        for c, text in enumerate(cells):
            if text == "":
                continue
            ref = f"{chr(65 + c)}{r}"
            try:
                float(text)
                cs.append(f'<c r="{ref}"><v>{text}</v></c>')
            except ValueError:
                strings.append(text)
                cs.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
        rows.append(f'<row r="{r}">{"".join(cs)}</row>')
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Other" sheetId="1" r:id="rId1"/><sheet name="{sheet}" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{ns}">' + "".join(f"<si><t>{s.replace('&', '&amp;')}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData/></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", f'<worksheet xmlns="{ns}"><sheetData>{"".join(rows)}</sheetData></worksheet>')
    return buf.getvalue()


def test_worldbank_xlsx_reader_matches_csv_grid(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    grid = worldbank.read_csv_grid(raw)
    xlsx = _xlsx(grid)
    from_xlsx = worldbank.read_xlsx_sheet(xlsx)
    def trim(rows):
        return [[c for c in r][: len(r) - next((i for i, c in enumerate(reversed(r)) if c != ""), len(r))] for r in rows]
    assert trim(from_xlsx) == trim(grid)
    a = worldbank.parse_xlsx(xlsx, m["fetched_at"])
    b = worldbank.parse_grid(grid, xlsx, m["fetched_at"])
    assert dumps(a) == dumps(b) and len(a) > 100


def test_worldbank_missing_sheet_fails_naming_source(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    with pytest.raises(SourceError, match=r"^\[worldbank\].*cannot read sheet"):
        worldbank.parse_xlsx(_xlsx(worldbank.read_csv_grid(raw), sheet="Renamed"), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[worldbank\].*cannot read sheet"):
        worldbank.parse_xlsx(b"not a zip", m["fetched_at"])


def test_worldbank_renamed_column_and_changed_unit_fail(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    with pytest.raises(SourceError, match=r"^\[worldbank\].*'Natural gas, Europe' is missing"):
        worldbank.parse_csv_extract(raw.replace(b"Natural gas, Europe", b"Natural gas, EU"), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[worldbank\].*unit"):
        worldbank.parse_csv_extract(raw.replace(b"($/mt)", b"(c/mt)"), m["fetched_at"])


def test_worldbank_text_value_bad_label_and_missing_date_fail(fixture_bytes):
    raw, m = fixture_bytes("worldbank", CSV)
    with pytest.raises(SourceError, match=r"^\[worldbank\].*not numeric"):
        worldbank.parse_csv_extract(raw.replace(b"2026M08,135.2,", b"2026M08,abc,"), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[worldbank\].*unrecognised period"):
        worldbank.parse_csv_extract(raw.replace(b"2026M08,", b"Aug 2026,"), m["fetched_at"])
    with pytest.raises(SourceError, match=r"^\[worldbank\].*Updated on"):
        worldbank.parse_csv_extract(raw.replace(b"Updated on", b"Refreshed"), m["fetched_at"])
