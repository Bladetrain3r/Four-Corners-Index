"""HTTP GET with bounded retries, polite spacing and secret redaction. Standard library only.

Never puts a key in an exception, a log line or a recorded URL: `redact` runs on everything that leaves this module.
"""
from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from pipeline.common import SourceError

SECRET_ENV = ("EIA_API_KEY", "ENTSOE_TOKEN")
USER_AGENT = "four-corners-index/0 (+https://github.com/Bladetrain3r/Four-Corners-Index)"
_KEY_PARAM = re.compile(r"((?:api_key|apikey|token|securityToken)=)[^&\s\"']+", re.IGNORECASE)
RETRY_STATUS = {429, 500, 502, 503, 504}
Opener = Callable[[str, dict[str, str], float], tuple[int, bytes, dict[str, str]]]
_last_call: dict[str, float] = {}


def redact(text: str) -> str:
    text = _KEY_PARAM.sub(r"\1REDACTED", text)
    for name in SECRET_ENV:
        value = os.environ.get(name)
        if value and len(value) > 8:
            text = text.replace(value, "REDACTED")
    return text


def _urlopen(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() or b"", dict(exc.headers or {})


def get(source: str, url: str, *, headers: dict[str, str] | None = None, retries: int = 3, backoff: float = 2.0,
        timeout: float = 120.0, min_interval: float = 0.5, opener: Opener = _urlopen,
        sleep: Callable[[float], Any] = time.sleep) -> tuple[bytes, dict[str, str]]:
    """GET `url`. Retries 429/5xx and network errors with exponential backoff; 4xx fails at once."""
    if not url.startswith("https://"):
        raise SourceError(source, f"refusing non-https URL {redact(url)}")
    host = urlsplit(url).netloc
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    last = "no attempt made"
    for attempt in range(retries + 1):
        wait = min_interval - (time.monotonic() - _last_call.get(host, -1e9))
        if wait > 0:
            sleep(wait)
        _last_call[host] = time.monotonic()
        try:
            status, body, resp_headers = opener(url, hdrs, timeout)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last = f"network error {type(exc).__name__}: {redact(str(exc))}"
        else:
            if status == 200:
                return body, resp_headers
            snippet = redact(body[:120].decode("utf-8", "replace").replace("\n", " "))
            last = f"HTTP {status}: {snippet}"
            if status not in RETRY_STATUS:
                raise SourceError(source, f"GET {redact(url)} failed, {last}")
        if attempt < retries:
            sleep(backoff * (2 ** attempt))
    raise SourceError(source, f"GET {redact(url)} failed after {retries + 1} attempts, {last}")
