"""The feedback receiver over real HTTP on a free port: what it accepts, what it refuses, what it keeps, what it never keeps."""

import json
import os
import stat
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

import pytest

from feedback import server

SITE = "https://example.org"


@pytest.fixture
def srv(tmp_path):
    def start(limiter=None, notify=None, trust_proxy=False, origins=(SITE,)):
        store = server.Store(tmp_path / f"data{len(started)}" / "feedback.jsonl")
        httpd = server.make_server("127.0.0.1", 0, store, set(origins), limiter=limiter, notify=notify, trust_proxy=trust_proxy)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}", store

    started: list = []
    yield start
    for h in started:
        h.shutdown()
        h.server_close()


def post(base, doc, *, origin=SITE, ctype="application/json", raw=None, headers=None):
    body = raw if raw is not None else json.dumps(doc).encode()
    req = urllib.request.Request(base + "/feedback", data=body, method="POST", headers={"Content-Type": ctype, **({"Origin": origin} if origin else {}), **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), dict(e.headers)


OK = {"v": 1, "vote": "up", "page": "/air.html"}


def test_a_valid_vote_is_stored_with_only_what_was_sent_and_the_cors_header_is_exact(srv):
    base, store = srv()
    status, body, h = post(base, {**OK, "comment": "Useful, thanks", "email": "a.b+c@example.com"})
    assert status == 200 and body == {"ok": True} and h["Access-Control-Allow-Origin"] == SITE and h["Cache-Control"] == "no-store"
    (row,) = store.rows()
    assert set(row) == {"id", "received", "vote", "page", "comment", "email", "reply"}  # no address, no user agent, nothing else
    assert (row["vote"], row["page"], row["comment"], row["email"], row["reply"]) == ("up", "/air.html", "Useful, thanks", "a.b+c@example.com", True)
    assert datetime.fromisoformat(row["received"]) <= datetime.now(UTC)


def test_comment_and_email_are_optional_and_empty_strings_count_as_absent(srv):
    base, store = srv()
    assert post(base, {**OK, "vote": "down", "comment": "", "email": ""})[0] == 200
    assert post(base, {**OK, "vote": "down"})[0] == 200
    assert [(r["comment"], r["email"], r["reply"]) for r in store.rows()] == [(None, None, False)] * 2


@pytest.mark.parametrize("doc,why", [
    ({**OK, "vote": "meh"}, "vote"), ({**OK, "vote": None}, "vote"), ({**OK, "v": 2}, "version"), ({**OK, "extra": 1}, "unknown field"),
    ({**OK, "page": "https://evil.example/x"}, "page"), ({**OK, "page": "/a" * 120}, "page"), ({**OK, "comment": "x" * 1001}, "comment"),
    ({**OK, "comment": "bell\x07"}, "comment"), ({**OK, "comment": 5}, "comment"), ({**OK, "email": "no-at-sign"}, "email"),
    ({**OK, "email": "a@b.com\nBcc: x@y.com"}, "email"), ({**OK, "email": "a b@c.com"}, "email"), ({**OK, "email": "a@" + "b" * 250 + ".com"}, "email"),
    (["not", "an", "object"], "JSON object"),
])
def test_anything_malformed_is_refused_with_a_reason_and_nothing_is_stored(srv, doc, why):
    base, store = srv()
    status, body, _ = post(base, doc)
    assert status == 400 and why in body["error"] and store.rows() == []


def test_a_filled_honeypot_is_answered_as_success_and_dropped(srv):
    base, store = srv()
    status, body, _ = post(base, {**OK, "website": "http://spam.example"})
    assert (status, body) == (200, {"ok": True}) and store.rows() == []


def test_body_size_content_type_and_json_are_enforced(srv):
    base, store = srv()
    assert post(base, None, raw=b"{" + b" " * 5000 + b"}")[0] == 413
    assert post(base, OK, ctype="text/plain")[0] == 415
    assert post(base, None, raw=b"not json")[0] == 400
    assert post(base, None, raw=b"\xff\xfe")[0] == 400
    assert store.rows() == []


def test_a_foreign_origin_is_refused_and_a_preflight_is_answered_only_for_the_site(srv):
    base, store = srv()
    status, _, h = post(base, OK, origin="https://evil.example")
    assert status == 403 and "Access-Control-Allow-Origin" not in h and store.rows() == []
    ok = urllib.request.Request(base + "/feedback", method="OPTIONS", headers={"Origin": SITE, "Access-Control-Request-Method": "POST"})
    with urllib.request.urlopen(ok, timeout=5) as r:
        assert r.status == 204 and r.headers["Access-Control-Allow-Origin"] == SITE and "POST" in r.headers["Access-Control-Allow-Methods"] and r.headers["Access-Control-Allow-Headers"] == "Content-Type"
    bad = urllib.request.Request(base + "/feedback", method="OPTIONS", headers={"Origin": "https://evil.example"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(bad, timeout=5)
    assert e.value.code == 403


def test_other_paths_are_404_and_healthz_answers(srv):
    base, _ = srv()
    with urllib.request.urlopen(base + "/healthz", timeout=5) as r:
        assert json.loads(r.read()) == {"ok": True}
    for path in ("/", "/admin", "/feedback/x"):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + path, timeout=5)
        assert e.value.code == 404


def test_rate_limit_per_client_with_retry_after_and_the_forwarded_address_only_behind_a_trusted_proxy(srv):
    base, store = srv(limiter=server.RateLimiter(per_hour=2, per_day=10))
    assert [post(base, OK)[0] for _ in range(3)] == [200, 200, 429]
    status, _, h = post(base, OK)
    assert status == 429 and int(h["Retry-After"]) > 0 and len(store.rows()) == 2
    # without --trust-proxy the header is ignored, so a spoofed address buys nothing
    assert post(base, OK, headers={"X-Forwarded-For": "203.0.113.9"})[0] == 429
    base2, _ = srv(limiter=server.RateLimiter(per_hour=1, per_day=10), trust_proxy=True)
    assert post(base2, OK, headers={"X-Forwarded-For": "198.51.100.1"})[0] == 200
    assert post(base2, OK, headers={"X-Forwarded-For": "198.51.100.2"})[0] == 200  # another client, behind the proxy
    assert post(base2, OK, headers={"X-Forwarded-For": "6.6.6.6, 198.51.100.2"})[0] == 429  # a client cannot choose its own key: the last entry is the proxy's


def test_the_daily_limit_applies_after_the_hourly_one():
    t = [0.0]
    rl = server.RateLimiter(per_hour=3, per_day=4, clock=lambda: t[0])
    assert [rl.allow("a") for _ in range(3)] == [0, 0, 0] and rl.allow("a") > 0
    t[0] = 3700
    assert rl.allow("a") == 0 and rl.allow("a") > 3600  # fifth in the day: the day limit, not the hour
    t[0] = 87000
    assert rl.allow("a") == 0


def test_the_store_is_owner_readable_only_and_append_only(srv):
    base, store = srv()
    post(base, OK)
    post(base, {**OK, "vote": "down"})
    assert stat.S_IMODE(os.stat(store.path).st_mode) == 0o600 and [r["vote"] for r in store.rows()] == ["up", "down"]
    assert len({r["id"] for r in store.rows()}) == 2


def test_prune_removes_comment_and_email_after_the_retention_period_and_keeps_the_vote(tmp_path):
    store = server.Store(tmp_path / "f.jsonl")
    old = store.append({"vote": "down", "page": "/", "comment": "old comment", "email": "o@example.com", "reply": True})
    new = store.append({"vote": "up", "page": "/", "comment": "new comment", "email": None, "reply": False})
    now = datetime.fromisoformat(old["received"]) + timedelta(days=91)
    lines = store.path.read_text().splitlines()
    # make the second entry recent relative to `now`
    row = json.loads(lines[1])
    row["received"] = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    store.path.write_text(lines[0] + "\n" + json.dumps(row) + "\n")
    assert store.prune(90, now=now) == 1
    a, b = store.rows()
    assert (a["comment"], a["email"], a["vote"], a["page"]) == (None, None, "down", "/") and "redacted" in a and b["comment"] == "new comment"
    assert store.prune(90, now=now) == 0 and stat.S_IMODE(os.stat(store.path).st_mode) == 0o600
    assert new["id"] == b["id"]


def test_report_counts_and_only_shows_comments_when_asked(tmp_path):
    store = server.Store(tmp_path / "f.jsonl")
    store.append({"vote": "up", "page": "/a", "comment": "secret words", "email": "x@example.com", "reply": True})
    store.append({"vote": "down", "page": "/b", "comment": None, "email": None, "reply": False})
    plain, full = server.report(store, False), server.report(store, True)
    assert "2 entries: 1 up, 1 down; 1 with a comment, 1 asking for a reply" in plain and "secret words" not in plain and "x@example.com" not in plain
    assert "secret words" in full and "x@example.com" in full


def test_mail_is_sent_with_reply_to_when_an_email_was_given_and_a_failing_mail_never_loses_the_entry(srv, monkeypatch):
    sent = []
    base, _ = srv(notify=lambda row: sent.append(row))
    post(base, {**OK, "comment": "hello", "email": "r@example.com"})
    deadline = time.time() + 3
    while not sent and time.time() < deadline:
        time.sleep(0.02)
    assert sent and sent[0]["comment"] == "hello"

    def boom(row):
        raise RuntimeError("smtp down")

    base2, store2 = srv(notify=boom)
    assert post(base2, OK)[0] == 200 and len(store2.rows()) == 1  # stored, answered, and the mail failure stayed in the log


def test_the_smtp_message_has_a_safe_subject_reply_to_and_no_credentials_in_it(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["conn"] = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            captured["tls"] = True

        def login(self, u, p):
            captured["login"] = (u, p)

        def send_message(self, msg):
            captured["msg"] = msg

    monkeypatch.setattr(server.smtplib, "SMTP", FakeSMTP)
    env = {"FEEDBACK_SMTP_HOST": "smtp.example", "FEEDBACK_SMTP_PORT": "2587", "FEEDBACK_MAIL_TO": "me@example.com", "FEEDBACK_MAIL_FROM": "feedback@example.org",
           "FEEDBACK_SMTP_USER": "u", "FEEDBACK_SMTP_PASS": "p"}
    send = server.smtp_notifier(env)
    send({"vote": "down", "page": "/air.html", "received": "2026-10-09T10:00:00Z", "comment": "line1\nline2", "email": "r@example.com"})
    m = captured["msg"]
    assert captured["conn"] == ("smtp.example", 2587) and captured["tls"] and captured["login"] == ("u", "p")
    assert m["Reply-To"] == "r@example.com" and m["To"] == "me@example.com" and m["Subject"] == "Four Corners Index feedback: down on /air.html"
    assert "line1\nline2" in m.get_content() and "p" not in m["Subject"].split(":")[0]
    assert server.smtp_notifier({}) is None and server.smtp_notifier({"FEEDBACK_SMTP_HOST": "x"}) is None  # all three, or no mail


def test_no_address_and_no_body_reaches_the_log(srv, capfd):
    base, _ = srv()
    post(base, {**OK, "comment": "very private words", "email": "private@example.com"})
    err = capfd.readouterr().err
    assert "POST /feedback 200" in err and "very private words" not in err and "private@example.com" not in err and "127.0.0.1" not in err
