// Header, navigation, theme toggle and footer shared by every page.
import { el, getJSON, store, $ } from "./util.js";

const NAV = [["index.html", "Overview"], ["indices.html", "The indices"], ["region.html?r=EU", "Regions", "region.html"], ["air.html", "Air quality"], ["method.html", "Method"], ["sources.html", "Sources"], ["downloads.html", "Downloads"]];
const THEMES = [["auto", "Theme: auto"], ["light", "Theme: light"], ["dark", "Theme: dark"]];

function applyTheme(t) {
  if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  else document.documentElement.removeAttribute("data-theme");
}

export async function initPage(page) {
  applyTheme(store.get("theme", "auto"));
  const here = location.pathname.split("/").pop() || "index.html";
  const themeBtn = el("button", { class: "theme", type: "button" });
  const label = () => { themeBtn.textContent = THEMES.find((t) => t[0] === store.get("theme", "auto"))[1]; };
  themeBtn.addEventListener("click", () => {
    const cur = store.get("theme", "auto");
    const next = THEMES[(THEMES.findIndex((t) => t[0] === cur) + 1) % THEMES.length][0];
    store.set("theme", next);
    applyTheme(next);
    label();
    window.dispatchEvent(new CustomEvent("themechange"));
  });
  label();
  const nav = el("nav", { class: "main", "aria-label": "Main" }, NAV.map(([href, text, match]) => el("a", { href, "aria-current": (match || href) === here ? "page" : null }, text)));
  $("#site-header").replaceWith(el("header", { class: "site" }, el("div", { class: "wrap" }, el("a", { class: "brand", href: "index.html" }, "Four Corners Index"), nav, themeBtn)));
  const skip = el("a", { class: "skip", href: "#main" }, "Skip to content");
  document.body.prepend(skip);
  const main = $("#main");
  main.append(el("p", { class: "muted", role: "status", id: "loading" }, "Loading data…"));
  try {
    const [src, meta] = await Promise.all([getJSON("data/sources.json"), getJSON("data/meta.json")]);
    $("#site-footer").replaceWith(footer(src, meta));
    const failing = Object.entries(meta.health || {}).filter(([, h]) => h.status === "failed");
    if (failing.length) {
      main.prepend(el("div", { class: "notice", role: "status", "data-testid": "health-banner" }, el("strong", {}, "A data source is failing. "),
        "The figures that depend on it are the last good ones: ", failing.map(([id, h]) => `${id} (last good ${h.last_good || "date not recorded"}, failing since ${h.failing_since})`).join("; "), ". ",
        el("a", { href: "sources.html" }, "Source health")));
    }
    return { main, src, meta, page };
  } catch (e) {
    $("#site-footer").replaceWith(el("footer", { class: "site" }, el("div", { class: "wrap" }, el("p", {}, "Attribution could not be loaded; see the Sources page and the repository."))));
    return { main, page, error: e };
  }
}

function footer(src, meta) {
  return el("footer", { class: "site" }, el("div", { class: "wrap" },
    el("p", {}, el("strong", {}, "Sources. "), "Every figure shows its source and age. Attribution, in the form each licence asks for:"),
    el("ul", {}, src.used.map((s) => el("li", {}, s.attribution))),
    el("p", {}, el("a", { href: "sources.html" }, "Licences, modifications and sources not used"), " · ", el("a", { href: "method.html" }, "Method"), " · ",
      el("a", { href: "https://github.com/Bladetrain3r/Four-Corners-Index" }, "Code and ledger on GitHub (MIT)")),
    el("p", {}, el("a", { href: src.sponsor.url }, "Sponsor this project"), ". ", src.sponsor.line),
    el("p", {}, src.disclaimer),
    el("p", { class: "meta", "data-testid": "health-line" }, healthLine(meta)),
    el("p", { class: "meta" }, `Data build ${meta.published} · method version ${meta.method_doc_version} · inputs ${meta.inputs_sha256.slice(0, 12)}`)));
}

function healthLine(meta) {
  const h = Object.values(meta.health || {});
  if (!h.length) return "Source health: not recorded.";
  const failing = h.filter((x) => x.status === "failed").length;
  const last = h.map((x) => x.last_good).filter(Boolean).sort().pop();
  return failing ? `Source health: ${failing} of ${h.length} sources failing; the rest last fetched ${last}.` : `Source health: all ${h.length} fetched sources fetched and parsed on ${last}.`;
}
