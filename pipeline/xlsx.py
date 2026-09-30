"""Stdlib spreadsheet helpers shared by adapters: read a sheet of an XLSX into a grid of strings, read CSV extractions.

Not an adapter: adapters import this instead of each other. `source` names the caller in any SourceError.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from xml.etree import ElementTree as ET

from pipeline.common import SourceError

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
SHEET_MARK = "### sheet: "


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)  # type: ignore[union-attr]
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx_sheet(raw: bytes, sheet: str, source: str) -> list[list[str]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = next(s.get(f"{{{NS['r']}}}id") for s in wb.find("m:sheets", NS) if s.get("name") == sheet)
        target = next(r.get("Target") for r in rels if r.get("Id") == rid)
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        path = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        ws = ET.fromstring(z.read(path))
    except (zipfile.BadZipFile, KeyError, StopIteration, ET.ParseError) as exc:
        raise SourceError(source, f"cannot read sheet {sheet!r} from the workbook ({exc!r})") from exc
    grid: list[list[str]] = []
    for row in ws.iter(f"{{{NS['m']}}}row"):
        cells: dict[int, str] = {}
        for c in row:
            v = c.find("m:v", NS)
            if c.get("t") == "s" and v is not None:
                text = shared[int(v.text)]
            elif c.get("t") == "inlineStr":
                text = "".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t"))
            else:
                text = v.text if v is not None and v.text is not None else ""
            cells[_col_index(c.get("r"))] = text
        r = int(row.get("r")) - 1
        while len(grid) <= r:
            grid.append([])
        grid[r] = [cells.get(i, "") for i in range(max(cells) + 1)] if cells else []
    return grid


def read_csv_grid(raw: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))


def split_csv_sheets(raw: bytes) -> dict[str, list[list[str]]]:
    """A CSV extraction holding several sheets, each introduced by a '### sheet: <name>' row."""
    sheets: dict[str, list[list[str]]] = {}
    cur: list[list[str]] | None = None
    for row in read_csv_grid(raw):
        if row and row[0].startswith(SHEET_MARK):
            cur = sheets.setdefault(row[0][len(SHEET_MARK):].strip(), [])
        elif cur is not None:
            cur.append(row)
    return sheets
