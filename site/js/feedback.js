// The feedback form in the footer: a thumbs up or down, an optional comment, an optional email to reply to.
// It does nothing and contacts no one until the visitor presses Send. It is only built when the site config names an endpoint.
import { el } from "./util.js";

export function feedbackBlock(cfg, page) {
  let vote = null;
  const status = el("p", { class: "meta", role: "status", "data-testid": "feedback-status" });
  const up = el("button", { type: "button", class: "vote", "aria-pressed": "false", "data-vote": "up" }, "👍 Useful");
  const down = el("button", { type: "button", class: "vote", "aria-pressed": "false", "data-vote": "down" }, "👎 Not useful");
  const comment = el("textarea", { id: "fb-comment", rows: "3", maxlength: String(cfg.max_comment), name: "comment", autocomplete: "off" });
  const email = el("input", { id: "fb-email", type: "email", name: "email", maxlength: "254", autocomplete: "email", placeholder: "you@example.com" });
  const trap = el("input", { type: "text", name: "website", tabindex: "-1", autocomplete: "off", "aria-hidden": "true" });
  const send = el("button", { type: "submit", class: "send", disabled: true }, "Send feedback");

  function choose(v) {
    vote = v;
    for (const b of [up, down]) b.setAttribute("aria-pressed", String(b.dataset.vote === v));
    send.disabled = false;
    status.textContent = "";
  }
  up.addEventListener("click", () => choose("up"));
  down.addEventListener("click", () => choose("down"));

  const form = el("form", { class: "feedback-form", novalidate: true },
    el("fieldset", {}, el("legend", {}, "Was this page useful?"), el("div", { class: "votes" }, up, down)),
    el("p", {}, el("label", { for: "fb-comment" }, "Anything to add? (optional)"), comment),
    el("p", {}, el("label", { for: "fb-email" }, "Email, only if you want a reply (optional)"), email),
    el("div", { class: "hp", "aria-hidden": "true" }, el("label", {}, "Leave this empty", trap)),
    send, status,
    el("p", { class: "meta", "data-testid": "feedback-privacy" },
      `We keep your vote and the page you were on. A comment and an email, if you give them, are kept for ${cfg.retention_days} days, only so we can read and reply, then deleted. `,
      `Your email is never shown on this site or shared. Nothing is sent until you press Send; it goes to ${cfg.host}. No cookies, no tracking. To have a message deleted sooner, contact ${cfg.contact}.`));

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!vote) { status.textContent = "Choose useful or not useful first."; return; }
    const addr = email.value.trim();
    if (addr && !email.checkValidity()) { status.textContent = "That email address does not look right. Fix it or leave it empty."; email.focus(); return; }
    send.disabled = true;
    status.textContent = "Sending…";
    const body = { v: 1, vote, page: page || "/", comment: comment.value.trim(), email: addr, website: trap.value };
    try {
      const r = await fetch(cfg.endpoint, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), credentials: "omit", referrerPolicy: "no-referrer", mode: "cors" });
      if (r.status === 429) throw new Error("You have sent a few already. Please try again later.");
      if (!r.ok) throw new Error("The server did not accept it.");
      form.reset();
      vote = null;
      for (const b of [up, down]) b.setAttribute("aria-pressed", "false");
      status.textContent = "Thank you. Your feedback was sent.";
    } catch (e) {
      send.disabled = false;
      status.textContent = `Could not send: ${e instanceof TypeError ? "the feedback server could not be reached" : e.message} Your text is still here.`;
      status.setAttribute("role", "alert");
    }
  });
  return el("details", { class: "feedback", "data-testid": "feedback" }, el("summary", {}, "Send feedback"), form);
}
