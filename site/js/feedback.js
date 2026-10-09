// Feedback: two links to a pre-filled GitHub issue form. No form, no request, no backend: nothing leaves the page until a visitor clicks and submits on GitHub.
import { el } from "./util.js";

export const REPO = "https://github.com/Bladetrain3r/Four-Corners-Index";
const FORMS = { up: { template: "feedback-up.yml", emoji: "👍", text: "Useful" }, down: { template: "feedback-down.yml", emoji: "👎", text: "Not useful" } };

// The page the visitor is on (path and query, so a region page says which region), as the form's "page" field.
export const pageOf = (loc = location) => "/" + (loc.pathname.split("/").pop() || "index.html") + loc.search;

export function feedbackUrl(kind, page) {
  const f = FORMS[kind];
  const q = new URLSearchParams({ template: f.template, title: `${f.emoji} ${f.text}: ${page}`, page });
  return `${REPO}/issues/new?${q}`;
}

export function feedbackLinks() {
  const page = pageOf();
  const link = (kind) => el("a", { class: "vote", href: feedbackUrl(kind, page), target: "_blank", rel: "noopener noreferrer", "data-testid": `feedback-${kind}` }, `${FORMS[kind].emoji} ${FORMS[kind].text}`);
  return el("div", { class: "feedback-links", "data-testid": "feedback" },
    el("p", {}, el("strong", {}, "Was this page useful?")),
    link("up"), link("down"),
    el("p", { class: "meta" }, "Opens a pre-filled GitHub issue. It is public and needs a GitHub account; we collect no email or other details here, and nothing is sent until you submit it on GitHub. ",
      el("a", { href: `${REPO}/issues`, "data-testid": "feedback-all" }, "All feedback and issues")));
}
