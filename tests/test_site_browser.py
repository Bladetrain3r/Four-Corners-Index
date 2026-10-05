"""G5 browser tests: the built site in headless Chromium at desktop and phone width. Skipped where Playwright or Chromium is absent."""

import functools
import glob
import http.server
import json
import os
import re
import shutil
import threading
import urllib.request
from pathlib import Path

import pytest

from pipeline import publish

pw = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parent.parent
CHROMIUM = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome") or [None])[0] or os.environ.get("CHROMIUM_PATH")
pytestmark = pytest.mark.skipif(not CHROMIUM or not Path(CHROMIUM).exists(), reason="no Chromium available")
SHOTS = ROOT / "evidence" / "G5"
PAGES = ["index.html", "indices.html", "air.html", "region.html?r=EU", "region.html?r=CN", "region.html?r=RU", "method.html", "sources.html", "downloads.html"]


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    d = tmp_path_factory.mktemp("served")
    for p in ROOT.joinpath("site").iterdir():
        if p.name not in ("data", "downloads"):
            shutil.copytree(p, d / p.name) if p.is_dir() else shutil.copy(p, d / p.name)
    publish.publish(d)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(d)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", d
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        yield b
        b.close()


def _open(browser, base, path, width=1280, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.errors, page.hosts = [], set()
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: page.hosts.add(re.match(r"\w+://([^/]+)", r.url).group(1) if "://" in r.url else "data"))
    page.goto(f"{base[0]}/{path}")
    page.wait_for_selector("footer.site")
    page.wait_for_timeout(300)
    return page


def _shot(page, name):
    if os.environ.get("FCI_SCREENSHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / name), full_page=True)


def _idx(base):
    return json.loads((base[1] / "data" / "index.json").read_text())


@pytest.mark.parametrize("width,label", [(1280, "desktop"), (390, "phone")])
def test_headline_tiles_show_value_date_source_and_badge(browser, base, width, label):
    page = _open(browser, base, "index.html", width)
    idx = _idx(base)
    for key, rows, badge in (("retail", idx["retail"], "Quality C"), ("wholesale", idx["wholesale"], "Quality A")):
        last, tile = rows[-1], page.locator(f'[data-testid="{key}"]')
        assert tile.locator(f'[data-testid="{key}-value"]').inner_text().startswith(f"{last['level']:.3f}")
        assert tile.locator(f'[data-testid="{key}-index"]').inner_text() == f"{last['index']:.1f}"
        text = tile.inner_text()
        assert last["published"] in text and last["status"] in text and "Source:" in text and "Month:" in text
        assert badge in tile.locator(f'[data-testid="{key}-badge"]').inner_text()
    assert page.errors == [] and page.hosts == {base[0].split("//")[1]}
    _shot(page, f"home_{label}.png")
    page.close()


def test_missing_figures_are_shown_as_missing_with_the_reason(browser, base):
    page = _open(browser, base, "index.html")
    regions = json.loads((base[1] / "data" / "regions.json").read_text())["regions"]
    checked = 0
    for r in regions:
        for kind, c in r["cards"].items():
            row = page.locator(f'[data-testid="{r["id"]}-{kind}"]')
            if c["status"] == "gap":
                assert row.get_attribute("data-status") == "gap" and "No source" in row.inner_text() and c["reason"][:40] in row.inner_text()
                checked += 1
            else:
                assert row.get_attribute("data-status") == "value" and c["source"][:30] in row.inner_text()
    assert checked >= 8
    page.close()


def test_currency_and_variant_toggles_change_the_numbers_as_claimed(browser, base):
    page = _open(browser, base, "index.html")
    idx = _idx(base)
    last = idx["retail"][-1]
    fx = idx["fx"][last["m"]]
    value = lambda: page.locator('[data-testid="retail-value"]').inner_text()
    assert value().startswith(f"{last['level']:.3f}")
    page.get_by_role("radio", name="Euro").check()
    assert value().startswith(f"{last['level'] / fx['USD']:.3f}") and "EUR/kWh" in value()
    page.get_by_role("radio", name="Rand").check()
    assert value().startswith(f"{last['level'] * fx['ZAR'] / fx['USD']:.2f}") and "ZAR/kWh" in value()
    page.get_by_role("radio", name="US dollar").check()
    page.get_by_role("radio", name="Equal-weighted").check()
    assert value().startswith(f"{last['equal_level']:.3f}") and "not the headline" in page.locator('[data-testid="retail"]').inner_text()
    assert page.locator('[data-testid="retail-index"]').inner_text() == f"{last['equal_index']:.1f}"
    page.get_by_role("radio", name="Excluding China").check()
    assert value().startswith(f"{last['ex_level']:.3f}")
    page.get_by_role("radio", name="Weighted (headline)").check()
    assert value().startswith(f"{last['level']:.3f}") and "not the headline" not in page.locator('[data-testid="retail"]').inner_text()
    assert page.errors == []
    page.close()


def test_keyboard_reaches_controls_and_a_chart_reads_out_values(browser, base):
    page = _open(browser, base, "index.html")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    chart = page.locator(".chart").first
    chart.focus()
    page.keyboard.press("ArrowLeft")
    text = page.locator(".chart [aria-live]").first.inner_text()
    assert re.search(r"20\d\d", text) and re.search(r"\d\.\d{3}", text)
    page.get_by_role("button", name="View as table").first.click()
    assert page.locator(".datatable table").first.locator("tbody tr").count() >= 140
    page.close()


@pytest.mark.parametrize("path", PAGES)
def test_pages_load_clean_fit_a_phone_and_touch_only_this_host(browser, base, path):
    for width in (1280, 390):
        page = _open(browser, base, path, width)
        assert page.errors == [], (path, page.errors)
        assert page.hosts == {base[0].split("//")[1]}, (path, page.hosts)
        assert page.evaluate("document.documentElement.scrollWidth") <= width, (path, width)
        assert page.locator("h1").count() == 1 and "could not be loaded" not in page.content()
        body = page.locator("body").inner_text()
        assert "[object" not in body and "undefined" not in body and "NaN" not in body, path
        name = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
        keep = {390: ("indices_html", "region_html_r_eu", "region_html_r_ru"), 1280: ("indices_html", "region_html_r_eu", "region_html_r_cn", "sources_html", "downloads_html")}
        if name in keep[width]:  # a curated set: full-page PNGs are large, so not every page at both widths
            _shot(page, f"{name}_{'phone' if width == 390 else 'desktop'}.png")
        page.close()


def test_region_pages_show_components_reconciliation_and_reasons(browser, base):
    eu = _open(browser, base, "region.html?r=EU")
    assert eu.locator("table", has_text="Components total").locator("tbody tr").count() == 7
    assert "Ember" in eu.locator("#region-sources").inner_text()
    eu.close()
    ru = _open(browser, base, "region.html?r=RU")
    assert ru.locator('#region-prices [data-status="gap"]').count() == 3 and ru.locator('#region-prices [data-status="value"]').count() == 0
    assert ru.locator(".chart").count() >= 1  # the generation mix is still shown
    ru.close()


def test_every_download_link_responds(browser, base):
    page = _open(browser, base, "downloads.html")
    links = page.locator("table a[download]").evaluate_all("els => els.map(e => e.getAttribute('href'))")
    page.close()
    assert len(links) >= 190
    for href in links:
        with urllib.request.urlopen(f"{base[0]}/{href}") as r:
            assert r.status == 200 and int(r.headers["Content-Length"]) > 0, href


def test_dark_theme_is_selectable_and_persists(browser, base):
    page = _open(browser, base, "index.html")
    while "dark" not in page.locator("button.theme").inner_text():
        page.locator("button.theme").click()
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark"
    _shot(page, "home_dark.png")
    page.reload()
    page.wait_for_selector("footer.site")
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark"
    page.close()


def test_a_failing_source_shows_a_banner_and_its_last_good_date_on_every_page(browser, base):
    meta_path = base[1] / "data" / "meta.json"
    original = meta_path.read_text()
    meta = json.loads(original)
    meta["health"] = {k: {"status": "ok", "last_good": "2026-09-30"} for k in ("desnz", "ecb", "eia", "ember", "eurostat", "worldbank")}  # a fixed state, not today's
    meta_path.write_text(json.dumps(meta))
    assert "all 6 fetched sources" in _open(browser, base, "index.html").locator('[data-testid="health-line"]').inner_text()
    meta["health"]["eia"] = {"status": "failed", "last_good": "2026-09-28", "failing_since": "2026-09-29", "message": "eia: forced failure (test flag --force-fail)"}
    meta_path.write_text(json.dumps(meta))
    try:
        for path in ("index.html", "region.html?r=US"):
            page = _open(browser, base, path)
            banner = page.locator('[data-testid="health-banner"]').inner_text()
            assert "eia" in banner and "last good 2026-09-28" in banner and "failing since 2026-09-29" in banner
            assert "1 of 6 sources failing" in page.locator('[data-testid="health-line"]').inner_text()
            if path == "index.html" and os.environ.get("FCI_SCREENSHOTS"):
                SHOTS.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(SHOTS / "failing_source_banner.png"))  # the top of the page only
            page.close()
        page = _open(browser, base, "sources.html")
        assert "Failing since 2026-09-29" in page.locator('[data-testid="health-eia"]').inner_text() and "Last good 2026-09-28" in page.locator('[data-testid="health-eia"]').inner_text()
        assert "fetched and parsed fine" in page.locator('[data-testid="health-ecb"]').inner_text()
        assert "kept by hand" in page.locator('[data-testid="health-shanghai"]').inner_text()
        page.close()
    finally:
        meta_path.write_text(original)


def _air_doc_from_fixture(tmp_path):
    """The air.json the daily run's data would give, built from the real-response fixture."""
    import csv

    from pipeline import site_air, site_data
    from tests.test_site_air import write_series_from_fixture
    write_series_from_fixture(tmp_path)
    real_rows, real_meta = site_data.series_rows, site_data.meta
    site_data.series_rows = lambda n: list(csv.DictReader((tmp_path / "data" / "series" / f"{n}.csv").open(encoding="utf-8"))) if n == site_air.SERIES else real_rows(n)
    site_data.meta = lambda n: json.loads((tmp_path / "data" / "series" / f"{n}.meta.json").read_text()) if n == site_air.SERIES else real_meta(n)
    try:
        return site_air.air_doc()
    finally:
        site_data.series_rows, site_data.meta = real_rows, real_meta


def test_air_tab_shows_each_value_with_year_source_licence_guideline_and_a_table(browser, base, tmp_path):
    air_path = base[1] / "data" / "air.json"
    original = air_path.read_text()
    doc = _air_doc_from_fixture(tmp_path)
    air_path.write_text(json.dumps(doc))
    try:
        for width in (1280, 390):
            page = _open(browser, base, "air.html", width)
            for r in doc["regions"]:
                card = page.locator(f'[data-testid="air-{r["id"]}"]')
                assert card.locator(f'[data-testid="air-{r["id"]}-value"]').inner_text().startswith(f"{r['latest']['value']:.1f}")
                text = card.inner_text()
                assert str(r["latest"]["year"]) in text and "CC BY-4.0" in text and "× the WHO guideline" in text and "Quality B" in text and doc["as_of"] in text
            vals = [float(page.locator(f'[data-testid="air-row-{r["id"]}"] td').first.inner_text()) for r in sorted(doc["regions"], key=lambda r: -r["latest"]["value"])]
            assert vals == sorted(vals, reverse=True) and len(vals) == 6
            assert "image table" in page.locator('[data-testid="air-guideline-note"]').inner_text() and "not an index" in page.locator('[data-testid="air-method"]').inner_text() + page.locator("p.lede").inner_text()
            page.get_by_role("button", name="View as table").click()
            assert page.locator(".chartcard table tbody tr").count() == len(doc["regions"][0]["series"])
            assert page.errors == [] and page.evaluate("document.documentElement.scrollWidth") <= width
            if width == 1280 and os.environ.get("FCI_SCREENSHOTS"):
                _shot(page, "air_desktop.png")
            if width == 390 and os.environ.get("FCI_SCREENSHOTS"):
                _shot(page, "air_phone.png")
            page.close()
    finally:
        air_path.write_text(original)


def test_air_tab_without_data_says_so_and_still_explains_what_it_is(browser, base):
    air_path = base[1] / "data" / "air.json"
    original = air_path.read_text()
    from pipeline import site_air
    from tests.test_site_air import site_data
    real = site_data.series_rows
    site_data.series_rows = lambda n: (_ for _ in ()).throw(FileNotFoundError(n)) if n == site_air.SERIES else real(n)
    try:
        air_path.write_text(json.dumps(site_air.air_doc()))
    finally:
        site_data.series_rows = real
    try:
        page = _open(browser, base, "air.html")
        assert "No data yet" in page.locator('[data-testid="air-not-yet"]').inner_text() and page.locator('[data-testid="air-method"]').count() == 1
        assert page.locator("#air-cards").count() == 0 and page.errors == []
        page.close()
    finally:
        air_path.write_text(original)


def test_south_africa_shows_the_two_eskom_figures_with_their_caveats_and_the_sources_page_states_the_terms(browser, base):
    page = _open(browser, base, "index.html")
    hh, ind, wh = (page.locator(f'[data-testid="ZA-{k}"]') for k in ("household", "industrial", "wholesale"))
    assert hh.get_attribute("data-status") == "value" and ind.get_attribute("data-status") == "value" and wh.get_attribute("data-status") == "gap"
    assert "tariff year 2026/27" in hh.inner_text() and "low confidence" in hh.inner_text() and "municipal tariff" in hh.inner_text() and "ZAR" in hh.inner_text()
    assert "financial year 2025/26" in ind.inner_text() and "realised average price" in ind.inner_text()
    assert hh.locator("a").get_attribute("href").startswith("https://www.eskom.co.za/")
    page.get_by_role("radio", name="Rand").check()
    assert hh.locator(".v").inner_text().startswith("2.70")  # in rand the native figure shows as published
    page.close()
    src = _open(browser, base, "sources.html")
    card = src.locator('[data-testid="source-eskom"]').inner_text()
    assert "never fetched automatically" in card and "inverted commas and acknowledged" in card and "If Eskom objects" in card
    assert "clause 2.10" in src.locator("#sources-not-used").inner_text()
    src.close()


def test_the_indices_page_describes_the_revisions_it_lists_whatever_their_number(browser, base):
    revs = _idx(base)["revisions"]
    page = _open(browser, base, "indices.html")
    text = page.locator('[data-testid="revisions-summary"]').inner_text()
    assert text.startswith(f"Revisions so far: {len(revs)}.") and "restate every Retail month when the UK joined" in text
    later = [r for r in revs if r["published"] != revs[0]["published"]]
    assert (f"{len(later)} later" in text) == bool(later)
    assert page.locator("table", has_text="Was").locator("tbody tr").count() == len(revs)
    page.close()
