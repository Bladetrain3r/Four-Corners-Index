import { el, getJSON, fail, $ } from "./util.js";
import { initPage } from "./layout.js";

const { main, src, meta, error } = await initPage("sources");

function health(id) {
  const h = (meta.health || {})[id];
  if (!h) return el("p", { class: "meta", "data-testid": `health-${id}` }, "Health: a dated fact kept by hand, not fetched daily.");
  return h.status === "failed"
    ? el("p", { class: "notice", "data-testid": `health-${id}` }, el("strong", {}, "Failing since " + h.failing_since + ". "), `Last good ${h.last_good || "not recorded"}; the site shows that last good data. ${h.message}`)
    : el("p", { class: "meta", "data-testid": `health-${id}` }, `Health: fetched and parsed fine, last on ${h.last_good}.`);
}
$("#loading")?.remove();
if (error) fail(main, error);
else {
  main.append(el("p", { class: "lede" }, src.note),
    el("h2", { text: "Sources used" }),
    el("div", { class: "grid", id: "sources-used" }, src.used.map((s) => el("section", { class: "card", id: s.id, "data-testid": `source-${s.id}` },
      el("h3", {}, s.name),
      health(s.id),
      el("p", { class: "meta" }, "Licence: ", el("a", { href: s.licence_url }, s.licence)),
      el("p", {}, el("strong", {}, "Attribution: "), s.attribution),
      el("p", { class: "meta" }, el("strong", {}, "Datasets: "), s.datasets),
      el("p", { class: "meta" }, el("strong", {}, "What we change: "), s.modified),
      s.quote ? el("blockquote", {}, s.quote) : null))),
    el("h2", { text: "Sources not used, and why" }),
    el("ul", { id: "sources-not-used" }, src.not_used.map((n) => el("li", {}, el("strong", {}, n.name + ": "), n.reason))),
    el("h2", { text: "Sponsor and disclaimer" }),
    el("p", {}, src.sponsor.line, " ", el("a", { href: src.sponsor.url }, "Sponsor the maintainer")),
    el("p", {}, src.disclaimer));
}
