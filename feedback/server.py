"""Feedback receiver for the Four Corners Index: one endpoint, standard library only.

    python -m feedback.server serve --data /var/lib/feedback/feedback.jsonl --origins https://example.org
    python -m feedback.server prune --data ... --days 90     # drops comment and email older than N days, keeps the vote
    python -m feedback.server report --data ... [--comments]

What it accepts: POST /feedback with JSON {"v":1, "vote":"up"|"down", "comment"?, "email"?, "page", "website"?}. Nothing else.
What it keeps: the vote, the page path, a time, and (only if given) the comment and the email. No IP address is stored or logged, no cookie is
set, no user agent is kept. Comment and email are deleted by `prune` after the retention period; the vote stays as an aggregate.
What it refuses: unknown fields, bodies over 4 KB, anything not JSON, an origin that is not allowed, too many posts from one client.
A filled-in honeypot field ("website") is answered with success and dropped, so a bot learns nothing.
Mail (optional): set FEEDBACK_SMTP_HOST, FEEDBACK_MAIL_TO and FEEDBACK_MAIL_FROM (and _PORT, _USER, _PASS); Amazon SES works through its SMTP interface.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import smtplib
import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

MAX_BODY = 4096
MAX_COMMENT = 1000
MAX_EMAIL = 254
MAX_PAGE = 200
FIELDS = {"v", "vote", "comment", "email", "page", "website"}
EMAIL = re.compile(r"^[A-Za-z0-9._%+'\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+$")
PAGE = re.compile(r"^/[A-Za-z0-9_\-./?=&%]*$")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # everything but tab and newline


class Rejected(Exception):
    def __init__(self, status: int, reason: str):
        super().__init__(reason)
        self.status, self.reason = status, reason


def validate(doc: Any) -> dict[str, Any] | None:
    """The clean entry, or None for a honeypot hit (to be answered as success and dropped). Raises Rejected."""
    if not isinstance(doc, dict):
        raise Rejected(400, "expected a JSON object")
    if set(doc) - FIELDS:
        raise Rejected(400, "unknown field")
    if doc.get("v") != 1:
        raise Rejected(400, "unsupported version")
    if doc.get("website") not in (None, ""):
        return None
    if doc.get("vote") not in ("up", "down"):
        raise Rejected(400, "vote must be up or down")
    page = doc.get("page", "/")
    if not isinstance(page, str) or len(page) > MAX_PAGE or not PAGE.match(page):
        raise Rejected(400, "bad page")
    out: dict[str, Any] = {"vote": doc["vote"], "page": page, "comment": None, "email": None}
    comment = doc.get("comment")
    if comment not in (None, ""):
        if not isinstance(comment, str) or len(comment) > MAX_COMMENT or CONTROL.search(comment):
            raise Rejected(400, "bad comment")
        out["comment"] = comment.strip() or None
    email = doc.get("email")
    if email not in (None, ""):
        if not isinstance(email, str) or len(email) > MAX_EMAIL or not EMAIL.match(email):
            raise Rejected(400, "bad email")
        out["email"] = email
    return out


class RateLimiter:
    """At most `per_hour` posts an hour and `per_day` a day from one client key. In memory only; nothing about a client survives a restart."""

    def __init__(self, per_hour: int = 5, per_day: int = 20, clock: Callable[[], float] = time.monotonic):
        self.per_hour, self.per_day, self.clock = per_hour, per_day, clock
        self.seen: dict[str, deque[float]] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> int:
        """0 if allowed (and counted), else the seconds to wait."""
        now = self.clock()
        with self.lock:
            q = self.seen.setdefault(key, deque())
            while q and now - q[0] > 86400:
                q.popleft()
            hour = [t for t in q if now - t <= 3600]
            if len(hour) >= self.per_hour:
                return int(3600 - (now - hour[0])) + 1
            if len(q) >= self.per_day:
                return int(86400 - (now - q[0])) + 1
            q.append(now)
            if len(self.seen) > 10000:  # a flood of distinct clients must not grow memory without bound
                for k in [k for k, v in self.seen.items() if not v or now - v[-1] > 86400]:
                    self.seen.pop(k, None)
            return 0


class Store:
    """An append-only JSON-lines file, readable by its owner only."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        row = {"id": secrets.token_hex(6), "received": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), **entry}
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)
        return row

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def prune(self, days: int, now: datetime | None = None) -> int:
        """Remove the comment and the email from entries older than `days`; the vote, page and time stay. Returns how many entries changed."""
        cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
        changed = 0
        out = []
        for r in self.rows():
            if (r.get("comment") or r.get("email")) and datetime.fromisoformat(r["received"]) < cutoff:
                r["comment"] = r["email"] = None
                r["redacted"] = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
                changed += 1
            out.append(r)
        if changed:
            tmp = self.path.with_suffix(".tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.writelines(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in out)
            os.replace(tmp, self.path)
        return changed


def smtp_notifier(env: dict[str, str] | None = None) -> Callable[[dict[str, Any]], None] | None:
    """A function that mails one entry to the owner, or None if no mail is configured. Credentials come from the environment only."""
    env = dict(os.environ if env is None else env)
    host, to, frm = env.get("FEEDBACK_SMTP_HOST"), env.get("FEEDBACK_MAIL_TO"), env.get("FEEDBACK_MAIL_FROM")
    if not (host and to and frm):
        return None

    def send(entry: dict[str, Any]) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"Four Corners Index feedback: {entry['vote']} on {entry['page']}"[:120]
        msg["From"], msg["To"] = frm, to
        if entry.get("email"):
            msg["Reply-To"] = entry["email"]  # validated: no whitespace, no newline
        msg.set_content(f"Vote: {entry['vote']}\nPage: {entry['page']}\nReceived: {entry['received']}\n\n{entry.get('comment') or '(no comment)'}\n")
        with smtplib.SMTP(host, int(env.get("FEEDBACK_SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            if env.get("FEEDBACK_SMTP_USER"):
                s.login(env["FEEDBACK_SMTP_USER"], env.get("FEEDBACK_SMTP_PASS", ""))
            s.send_message(msg)

    return send


def make_server(host: str, port: int, store: Store, origins: set[str], *, limiter: RateLimiter | None = None,
                notify: Callable[[dict[str, Any]], None] | None = None, trust_proxy: bool = False) -> ThreadingHTTPServer:
    limiter = limiter or RateLimiter()

    class Handler(BaseHTTPRequestHandler):
        server_version = "feedback"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_request(self, code: Any = "-", size: Any = "-") -> None:  # method, path and status only: no address, no body
            sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {code}\n")

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("error " + (fmt % args).split(" - ")[0] + "\n")

        def _send(self, status: int, body: dict[str, Any] | None = None, extra: dict[str, str] | None = None) -> None:
            payload = json.dumps(body if body is not None else {}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(0 if status == 204 else len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if status != 204:
                self.wfile.write(payload)

        def _cors(self) -> dict[str, str] | None:
            origin = self.headers.get("Origin")
            if origin is None:
                return {}
            if origin in origins:
                return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
            return None

        def _client(self) -> str:
            peer = self.client_address[0]
            if trust_proxy and peer in ("127.0.0.1", "::1"):
                fwd = self.headers.get("X-Forwarded-For", "")
                if fwd:
                    return fwd.split(",")[-1].strip()  # the entry our own proxy appended
            return peer

        def do_GET(self) -> None:
            self._send(200, {"ok": True}) if self.path == "/healthz" else self._send(404, {"error": "not found"})

        def do_OPTIONS(self) -> None:
            cors = self._cors()
            if self.path != "/feedback" or not cors:
                return self._send(403 if cors is None else 404, {"error": "not allowed"})
            self._send(204, None, {**cors, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600"})

        def do_POST(self) -> None:
            cors = self._cors()
            if cors is None:
                return self._send(403, {"error": "origin not allowed"})
            if self.path != "/feedback":
                return self._send(404, {"error": "not found"}, cors)
            wait = limiter.allow(self._client())
            if wait:
                return self._send(429, {"error": "too many requests"}, {**cors, "Retry-After": str(wait)})
            if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
                return self._send(415, {"error": "send application/json"}, cors)
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._send(411, {"error": "length required"}, cors)
            if length < 0 or length > MAX_BODY:
                self.close_connection = True
                return self._send(413, {"error": "too large"}, {**cors, "Connection": "close"})
            try:
                entry = validate(json.loads(self.rfile.read(length)))
            except Rejected as e:
                return self._send(e.status, {"error": e.reason}, cors)
            except (ValueError, UnicodeDecodeError):
                return self._send(400, {"error": "not valid JSON"}, cors)
            if entry is not None:  # None: honeypot, answered as success and dropped
                row = store.append({**entry, "reply": bool(entry["email"])})
                if notify:
                    threading.Thread(target=_safe, args=(notify, row), daemon=True).start()
            self._send(200, {"ok": True}, cors)

    return ThreadingHTTPServer((host, port), Handler)


def _safe(fn: Callable[[dict[str, Any]], None], row: dict[str, Any]) -> None:
    try:
        fn(row)
    except Exception as e:  # noqa: BLE001  a failed mail must never lose or leak the entry: it is already stored
        sys.stderr.write(f"mail failed: {type(e).__name__}\n")


def report(store: Store, with_comments: bool) -> str:
    rows = store.rows()
    up, down = sum(r["vote"] == "up" for r in rows), sum(r["vote"] == "down" for r in rows)
    lines = [f"{len(rows)} entries: {up} up, {down} down; {sum(bool(r.get('comment')) for r in rows)} with a comment, {sum(bool(r.get('reply')) for r in rows)} asking for a reply"]
    for r in rows[-20:] if with_comments else []:
        lines.append(f"{r['received']} {r['vote']:4s} {r['page']}  {r.get('comment') or ''}  {('<' + r['email'] + '>') if r.get('email') else ''}".rstrip())
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--origins", required=True, help="comma-separated allowed origins, e.g. https://example.org,https://you.github.io")
    s.add_argument("--trust-proxy", action="store_true", help="take the client address from X-Forwarded-For when the peer is localhost (behind Caddy)")
    for name in ("serve", "prune", "report"):
        p = s if name == "serve" else sub.add_parser(name)
        p.add_argument("--data", type=Path, default=Path(os.environ.get("FEEDBACK_DATA", "feedback.jsonl")))
    sub.choices["prune"].add_argument("--days", type=int, required=True)
    sub.choices["report"].add_argument("--comments", action="store_true")
    a = ap.parse_args(argv)
    store = Store(a.data)
    if a.cmd == "prune":
        print(f"redacted {store.prune(a.days)} entries older than {a.days} days")
        return 0
    if a.cmd == "report":
        print(report(store, a.comments))
        return 0
    origins = {o.strip().rstrip("/") for o in a.origins.split(",") if o.strip()}
    if not origins or any(not o.startswith("https://") for o in origins):
        sys.exit("--origins must be https:// origins")
    srv = make_server(a.host, a.port, store, origins, notify=smtp_notifier(), trust_proxy=a.trust_proxy)
    sys.stderr.write(f"listening on {a.host}:{a.port}, origins {sorted(origins)}, mail {'on' if smtp_notifier() else 'off'}\n")
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
