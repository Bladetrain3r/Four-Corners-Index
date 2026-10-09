# Feedback receiver

A ~250-line, standard-library-only receiver for the footer feedback form. It runs on one small always-on host (your EC2 instance), behind Caddy for HTTPS,
and writes a JSON-lines file. Nothing else is needed: no database, no package install.

**What a visitor sends:** a vote (up or down), the page path, and, only if they type them, a comment (max 1,000 characters) and an email address to reply to.
**What is kept:** those, plus a received time and a random id. No IP address, no user agent, no cookie. The access log has method, path and status only.
**Retention:** `prune` deletes the comment and the email after N days (the site's config says N, default 90); the vote, page and time stay as an aggregate.
**What it refuses:** unknown fields, bodies over 4 KB, non-JSON, other origins, more than 5 posts an hour or 20 a day from one client, anything off the one path.
A filled-in hidden "website" field (a bot) is answered with success and dropped.

## Turn it on (about 20 minutes)

1. **Host and DNS.** On the instance (Amazon Linux or Ubuntu, any size that runs Python 3.12): point a name such as `feedback.<your domain>` at it. The page is
   served over HTTPS, so the receiver must be too, and browsers will not accept an IP address or a self-signed certificate for it.
2. **Security group.** Allow inbound 80 and 443 (Caddy needs 80 for the certificate) and nothing else from the internet; the receiver itself listens on
   `127.0.0.1:8787` only. SSH from your own address only.
3. **Install.** Copy this `feedback/` directory (and an empty `__init__.py` next to it as in the repo) to `/opt/four-corners/feedback/`, or `git clone` the repo there.
   Create the service user and data directory:
   ```
   sudo useradd --system --home /var/lib/feedback --shell /usr/sbin/nologin feedback
   sudo install -d -o feedback -g feedback -m 700 /var/lib/feedback
   ```
4. **Configure.** `sudo cp deploy/feedback.env.example /etc/feedback.env`, edit it (origins = the exact origins of the site, https only, no trailing slash: the
   github.io address now, the custom domain later, both while you move), `sudo chmod 600 /etc/feedback.env`.
5. **Run it.** `sudo cp deploy/feedback.service deploy/feedback-prune.service deploy/feedback-prune.timer /etc/systemd/system/` then
   `sudo systemctl daemon-reload && sudo systemctl enable --now feedback feedback-prune.timer`.
6. **HTTPS.** Install Caddy, put `deploy/Caddyfile.example` (with your host name) at `/etc/caddy/Caddyfile`, `sudo systemctl reload caddy`. Caddy gets and renews the
   certificate by itself. Check: `curl https://feedback.<your domain>/healthz` answers `{"ok": true}`.
7. **Switch the form on.** In this repo edit `data/manual/feedback.json`: set `endpoint` to `https://feedback.<your domain>/feedback`, `contact` to where a visitor can ask
   for deletion (an email address or a URL), and `retention_days`. Merge. The next Pages build shows the form in the footer of every page. (Both fields are required:
   the build refuses a form that collects an email and names nobody to ask.)
8. **Try it.** Send one from the site. Then, on the instance: `sudo -u feedback python3 -m feedback.server report --data /var/lib/feedback/feedback.jsonl --comments`.

## Mail (optional)
To get each message by email, set `FEEDBACK_SMTP_HOST`, `FEEDBACK_MAIL_TO` and `FEEDBACK_MAIL_FROM` (and `FEEDBACK_SMTP_PORT`, `FEEDBACK_SMTP_USER`,
`FEEDBACK_SMTP_PASS`) in `/etc/feedback.env`. Amazon SES works through its SMTP interface (verify the sender address in SES first; the SMTP credentials are
not your AWS keys). A visitor's email, if given, becomes the Reply-To, so replying is one click. If mail fails, the entry is already stored and the error is logged
without any of its content.

## Operating it
- Read: `python3 -m feedback.server report --data ... [--comments]`. The file is mode 0600, owned by the service user.
- Delete one person's message on request: edit the file and remove that line (find it by the time or the text), or redact it with `prune --days 0`.
- Back up? There is no need: it is a suggestion box. If you do, treat the file as personal data.
- Updating: replace the files, `sudo systemctl restart feedback`.
- If the endpoint is unreachable, visitors see "could not be reached" and keep their text. Nothing else on the site depends on it.

## Privacy, in one place
You are the responsible party for any email or comment collected (POPIA in South Africa; GDPR for visitors in the EU). The form tells visitors what is kept, for how
long, why, where it goes (the host name) and whom to ask. Do not add analytics, cookies or logging of addresses to this service without changing that text.
