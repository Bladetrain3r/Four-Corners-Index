import csv
import io

import pytest

from pipeline import desnz
from pipeline.common import SourceError, dumps

HH = "table_562_medium_domestic_eu_uk.csv"
NH = "table_542_medium_nondomestic_eu_uk.csv"


def _one(points, **want):
    hits = [p for p in points if all(p.get(k) == v for k, v in want.items())]
    assert len(hits) == 1, f"{len(hits)} matches for {want}"
    return hits[0]


def test_desnz_household_medium_uk_values_units_and_period(fixture_bytes, series_schema):
    raw, m = fixture_bytes("desnz", HH)
    pts = desnz.parse(raw, m["fetched_at"], "5.6.2", "fixture")
    for p in pts:
        series_schema.validate(p)
    p = _one(pts, series_id="desnz:qep_5.6.2:medium:incl_tax", period_start="2025-07-01")
    assert abs(p["value"] - 0.2977726) < 1e-7 and p["unit"] == "GBP/kWh" and p["currency"] == "GBP"  # 29.77726 pence/kWh
    assert p["region"] == "GB" and p["buyer_type"] == "household" and p["period_end"] == "2025-12-31"
    x = _one(pts, series_id="desnz:qep_5.6.2:medium:excl_tax", period_start="2025-07-01")
    assert abs(x["value"] - 0.2049629) < 1e-6


def test_desnz_keeps_only_the_2015_methodology(fixture_bytes):
    raw, m = fixture_bytes("desnz", HH)
    pts = desnz.parse(raw, m["fetched_at"], "5.6.2", "fixture")
    starts = sorted({p["period_start"] for p in pts})
    assert starts[0] == "2015-01-01" and starts[-1] == "2025-07-01" and len(starts) == 22
    assert not [p for p in pts if p["period_start"] < "2015-01-01"]


def test_desnz_non_household_is_band_id_and_industrial(fixture_bytes):
    raw, m = fixture_bytes("desnz", NH)
    pts = desnz.parse(raw, m["fetched_at"], "5.4.2", "fixture")
    p = _one(pts, series_id="desnz:qep_5.4.2:medium:incl_tax", period_start="2025-07-01")
    assert abs(p["value"] - 0.2507686) < 1e-6 and p["buyer_type"] == "industrial"


def test_desnz_xlsx_route_matches_the_csv_route(fixture_bytes):
    raw, m = fixture_bytes("desnz", HH)
    sheets = desnz.xlsx.split_csv_sheets(raw)
    # a real workbook with the two sheets, built from the same cells
    incl, excl = (sheets["5.6.2 (Medium incl tax)"], sheets["5.6.2 (Medium excl tax)"])
    wb = _two_sheet_xlsx(incl, excl)
    a = desnz.parse(wb, m["fetched_at"], "5.6.2", "live")
    b = desnz.parse(raw, m["fetched_at"], "5.6.2", "fixture")
    def strip(pts):
        return [{k: v for k, v in p.items() if k != "raw_sha256"} for p in pts]

    assert dumps(strip(a)) == dumps(strip(b)) and len(a) == 44


def _letters(c: int) -> str:
    out = ""
    c += 1
    while c:
        c, rem = divmod(c - 1, 26)
        out = chr(65 + rem) + out
    return out


def _two_sheet_xlsx(incl, excl):
    import zipfile
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    strings: list[str] = []

    def rows_xml(grid):
        out = []
        for r, cells in enumerate(grid, start=1):
            cs = []
            for c, text in enumerate(cells):
                if text == "":
                    continue
                ref = f"{_letters(c)}{r}"
                strings.append(text)
                cs.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
            out.append(f'<row r="{r}">{"".join(cs)}</row>')
        return "".join(out)

    s1, s2 = rows_xml(incl), rows_xml(excl)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="5.6.2 (Medium incl tax)" sheetId="1" r:id="rId1"/><sheet name="5.6.2 (Medium excl tax)" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{ns}">' + "".join(f"<si><t>{s.replace('&', '&amp;').replace('<', '&lt;')}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData>{s1}</sheetData></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", f'<worksheet xmlns="{ns}"><sheetData>{s2}</sheetData></worksheet>')
    return buf.getvalue()


def test_desnz_output_deterministic(fixture_bytes):
    raw, m = fixture_bytes("desnz", HH)
    assert dumps(desnz.parse(raw, m["fetched_at"], "5.6.2", "fixture")) == dumps(desnz.parse(raw, m["fetched_at"], "5.6.2", "fixture"))


def test_desnz_changed_band_unit_or_sheet_fails_naming_source(fixture_bytes):
    raw, m = fixture_bytes("desnz", HH)
    with pytest.raises(SourceError, match=r"^\[desnz\].*band definition"):
        desnz.parse(raw.replace(b"2,500 - 4,999 kWh", b"3,000 - 5,999 kWh"), m["fetched_at"], "5.6.2", "fixture")
    with pytest.raises(SourceError, match=r"^\[desnz\].*pence per kWh"):
        desnz.parse(raw.replace(b"In pence per kWh.", b"In pounds per kWh."), m["fetched_at"], "5.6.2", "fixture")
    with pytest.raises(SourceError, match=r"^\[desnz\].*not found"):
        desnz.parse(raw.replace(b"5.6.2 (Medium incl tax)", b"5.7.2 (Medium incl tax)"), m["fetched_at"], "5.6.2", "fixture")
    with pytest.raises(SourceError, match=r"^\[desnz\].*'United Kingdom' not found"):
        desnz.parse(raw.replace(b"United Kingdom", b"UK"), m["fetched_at"], "5.6.2", "fixture")
    with pytest.raises(SourceError, match=r"^\[desnz\].*not a workbook|cannot read sheet"):
        desnz.parse(b"not a zip", m["fetched_at"], "5.6.2", "live")


def test_desnz_text_value_blank_value_and_bad_period_fail(fixture_bytes):
    raw, m = fixture_bytes("desnz", HH)
    rows = list(csv.reader(io.StringIO(raw.decode())))
    i = next(n for n, r in enumerate(rows) if r[:2] == ["2025", "Jul – Dec"])
    uk = 17

    def edited(value=None, period=None):
        rr = [list(r) for r in rows]
        if value is not None:
            rr[i][uk] = value
        if period is not None:
            rr[i][1] = period
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows(rr)
        return buf.getvalue().encode()

    with pytest.raises(SourceError, match=r"^\[desnz\].*not numeric"):
        desnz.parse(edited(value="n/a"), m["fetched_at"], "5.6.2", "fixture")
    with pytest.raises(SourceError, match=r"^\[desnz\].*blank value"):
        desnz.parse(edited(value=""), m["fetched_at"], "5.6.2", "fixture")
    gaps: list = []
    pts = desnz.parse(edited(value=""), m["fetched_at"], "5.6.2", "fixture", gaps=gaps)
    assert len(gaps) == 1 and len(pts) == 43 and gaps[0]["region"] == "GB"  # the edit touches the incl-tax sheet only
    with pytest.raises(SourceError, match=r"^\[desnz\].*period label"):
        desnz.parse(edited(period="Q3"), m["fetched_at"], "5.6.2", "fixture")
    assert edited(value="29.7r")  # a revised marker is tolerated
    assert len(desnz.parse(edited(value="29.7r"), m["fetched_at"], "5.6.2", "fixture")) == 44
