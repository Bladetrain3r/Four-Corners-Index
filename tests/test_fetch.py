import urllib.error

import pytest

from pipeline import fetch, http, registry
from pipeline.common import SourceError


class FakeOpener:
    """Scripted responses: each call pops the next (status, body) or raises the given exception."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls: list[str] = []

    def __call__(self, url, headers, timeout):
        self.calls.append(url)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        status, body = item
        return status, body, {}


def NO_SLEEP(seconds):
    return None


def test_http_retries_5xx_then_succeeds():
    op = FakeOpener((500, b"Something unexpected happened."), (500, b"x"), (200, b"ok"))
    body, _ = http.get("eia", "https://example.org/x", opener=op, sleep=NO_SLEEP)
    assert body == b"ok" and len(op.calls) == 3


def test_http_4xx_fails_at_once_and_names_source():
    op = FakeOpener((403, b"Forbidden"), (200, b"never reached"))
    with pytest.raises(SourceError, match=r"^\[eurostat\].*HTTP 403"):
        http.get("eurostat", "https://example.org/x", opener=op, sleep=NO_SLEEP)
    assert len(op.calls) == 1


def test_http_gives_up_after_bounded_retries_and_network_errors_are_retried():
    op = FakeOpener(urllib.error.URLError("boom"), (503, b"a"), (503, b"b"), (503, b"c"))
    with pytest.raises(SourceError, match=r"^\[ecb\].*failed after 4 attempts"):
        http.get("ecb", "https://example.org/x", retries=3, opener=op, sleep=NO_SLEEP)
    assert len(op.calls) == 4


def test_http_refuses_plain_http():
    with pytest.raises(SourceError, match=r"^\[ember\].*non-https"):
        http.get("ember", "http://example.org/x", opener=FakeOpener(), sleep=NO_SLEEP)


def test_secret_never_appears_in_errors_or_redacted_urls(monkeypatch):
    monkeypatch.setenv("EIA_API_KEY", "S3CRETKEYVALUE1234567890")
    url = "https://api.eia.gov/v2/x?api_key=S3CRETKEYVALUE1234567890&a=1"
    assert "S3CRET" not in http.redact(url) and "api_key=REDACTED" in http.redact(url)
    op = FakeOpener((401, b'{"error":"invalid key S3CRETKEYVALUE1234567890"}'))
    with pytest.raises(SourceError) as exc:
        http.get("eia", url, opener=op, sleep=NO_SLEEP)
    assert "S3CRET" not in str(exc.value) and "REDACTED" in str(exc.value)
    with pytest.raises(SourceError) as exc2:
        http.get("eia", url, retries=0, opener=FakeOpener(urllib.error.URLError("proxy said S3CRETKEYVALUE1234567890")), sleep=NO_SLEEP)
    assert "S3CRET" not in str(exc2.value)


def _req(source, name):
    return next(r for r in registry.REQUESTS if r.source == source and r.name == name)


def test_fetch_fixture_mode_uses_manifest_time_and_url():
    loaded = fetch.load(_req("ecb", "exr_monthly"), "fixture")
    assert loaded.kind == "fixture" and loaded.retrieved_at.startswith("2026-09-29")
    assert len(fetch.parse(loaded)) > 100


def test_fetch_auto_without_key_falls_back_to_fixture_and_says_so(monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    loaded = fetch.load(_req("eia", "retail_price"), "auto", opener=FakeOpener())  # opener must not be called
    assert loaded.kind == "fixture" and "EIA_API_KEY absent" in loaded.note and "NOT current" in loaded.note


def test_fetch_live_without_key_raises_rather_than_serving_a_fixture(monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    with pytest.raises(SourceError, match=r"^\[eia\].*EIA_API_KEY is not set"):
        fetch.load(_req("eia", "retail_price"), "live", opener=FakeOpener())


def test_fetch_live_puts_key_in_request_but_never_in_result(monkeypatch):
    monkeypatch.setenv("EIA_API_KEY", "S3CRETKEYVALUE1234567890")
    fx = (fetch.FIXTURES / "eia" / "henry_hub_spot_monthly_2025-10_onwards.json").read_bytes()
    op = FakeOpener((200, fx))
    loaded = fetch.load(_req("eia", "henry_hub_monthly"), "live", opener=op, now=lambda: "2026-10-01T00:00:00Z")
    assert "api_key=S3CRETKEYVALUE1234567890" in op.calls[0]
    assert "S3CRET" not in loaded.url and "api_key=REDACTED" in loaded.url and loaded.kind == "live"
    assert len(fetch.parse(loaded)) == 11


def test_fetch_live_failure_raises_not_falls_back():
    op = FakeOpener((404, b"nope"))
    with pytest.raises(SourceError, match=r"^\[ecb\].*HTTP 404"):
        fetch.load(_req("ecb", "exr_daily"), "live", opener=op)


def test_pink_sheet_url_is_resolved_from_the_landing_page():
    html = b'<a href="https://thedocs.worldbank.org/en/doc/abc-0050012026/related/CMO-Historical-Data-Monthly.xlsx">x</a>'
    assert registry.resolve_pink_sheet_url(html).endswith("CMO-Historical-Data-Monthly.xlsx")
    with pytest.raises(SourceError, match=r"^\[worldbank\].*no CMO"):
        registry.resolve_pink_sheet_url(b"<html>redesigned</html>")


def test_every_registry_request_has_a_fixture_that_parses_and_no_key_in_url():
    assert len(registry.REQUESTS) == 17
    for req in registry.REQUESTS:
        assert "api_key=" not in req.url or "api_key={key}" in req.url
        loaded = fetch.load(req, "fixture")
        assert fetch.parse(loaded), req.name
