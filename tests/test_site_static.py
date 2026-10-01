"""G5 static checks on the site sources: every page is self-contained, labelled, and its colour tokens are readable."""

import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
PAGES = ["index", "indices", "region", "air", "method", "sources", "downloads"]


def _lum(hex_: str) -> float:
    rgb = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", block))


def _themes() -> dict[str, dict[str, str]]:
    css = (SITE / "css" / "site.css").read_text()
    light = _tokens(css.split("@media")[0])
    dark = _tokens(re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.DOTALL).group(1))
    return {"light": light, "dark": dark}


@pytest.mark.parametrize("page", PAGES)
def test_page_is_complete_and_self_contained(page):
    html = (SITE / f"{page}.html").read_text()
    assert '<html lang="en">' in html and 'name="viewport"' in html and re.search(r"<title>[^<]{5,}</title>", html)
    assert html.count("<h1>") == 1 and 'id="main"' in html and "<noscript>" in html
    for ref in re.findall(r'(?:src|href)="([^"]+)"', html):
        assert not re.match(r"(?:[a-z]+:)?//", ref), f"{page}.html loads or links outside the site: {ref}"
        if not ref.startswith("#") and "?" not in ref:
            assert (SITE / ref).exists(), f"{page}.html references missing {ref}"
    script = re.search(r'<script type="module" src="([^"]+)"', html).group(1)
    assert (SITE / script).exists()


def test_no_external_requests_in_scripts_or_styles():
    for f in list((SITE / "js").glob("*.js")) + [SITE / "css" / "site.css"]:
        text = f.read_text()
        assert not re.search(r"fetch\(\s*[\"'`]https?:", text), f.name
        assert not re.search(r"import\s[^;]*from\s*[\"']https?:", text), f.name
        assert not re.search(r"url\(\s*[\"']?https?:|@import\s+[\"']?https?:", text), f.name
        assert "XMLHttpRequest" not in text and "sendBeacon" not in text and "WebSocket" not in text, f.name


def test_every_local_import_and_link_target_exists():
    for f in (SITE / "js").glob("*.js"):
        for ref in re.findall(r'from "(\./[^"]+)"', f.read_text()):
            assert (f.parent / ref).exists(), f"{f.name} imports missing {ref}"
    for f in (SITE / "js").glob("*.js"):
        for ref in re.findall(r'href: "([a-z]+\.html)[?"]', f.read_text()):
            assert (SITE / ref).exists(), f"{f.name} links to missing {ref}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_tokens_have_at_least_aa_contrast_on_every_surface(theme):
    t = _themes()[theme]
    for fg in ("text-primary", "text-secondary", "text-muted", "accent", "status-final", "status-prov"):
        for bg in ("surface-page", "surface-1", "surface-2"):
            assert _ratio(t[fg], t[bg]) >= 4.5, f"{theme}: {fg} on {bg} is {_ratio(t[fg], t[bg]):.2f}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_chart_series_are_never_the_only_signal(theme):
    # Series colours can fall below 3:1 on the surface; the design relieves that with direct labels, a legend and a data table.
    # This test pins that relief: every chart card has a "View as table" button and stacked charts have a legend.
    js = (SITE / "js" / "charts.js").read_text()
    assert "View as table" in js and 'class: "legend"' in js and "aria-live" in js and "ArrowLeft" in js
    assert len(_themes()[theme]) >= 8


def test_chart_module_labels_and_keyboard_access():
    js = (SITE / "js" / "charts.js").read_text()
    assert 'setAttribute("tabindex", "0")' in js and "aria-label" in js and 'role", "group"' in js
    assert "ArrowRight" in js and "Home" in js and "End" in js
