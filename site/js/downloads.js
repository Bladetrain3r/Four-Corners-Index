import { el, getJSON, fail, $, num } from "./util.js";
import { initPage } from "./layout.js";

const size = (b) => (b >= 1e6 ? `${num(b / 1e6, 1)} MB` : `${num(Math.max(b / 1e3, 0.1), 1)} kB`);

const { main, error } = await initPage("downloads");
$("#loading")?.remove();
if (error) fail(main, error);
else {
  try {
    const d = await getJSON("data/downloads.json");
    const groups = new Map();
    for (const i of d.items) groups.set(i.group, [...(groups.get(i.group) || []), i]);
    main.append(el("p", { class: "lede" }, "Every number on this site is a file here. CSV and JSON carry the same values; the ledger is hash-chained and can be checked with ledger/verify.py from the repository."));
    for (const [g, items] of groups) {
      main.append(el("h2", { text: g }), el("div", { class: "datatable tablewide text", tabindex: "0", role: "region", "aria-label": `${g} downloads (scrollable)` },
        el("table", {}, el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "File"), el("th", { scope: "col" }, "What it is"), el("th", { scope: "col" }, "Size"))),
          el("tbody", {}, items.map((i) => el("tr", {}, el("th", { scope: "row" }, el("a", { href: i.path, download: "" }, i.name)), el("td", {}, i.description), el("td", {}, size(i.bytes))))))));
    }
  } catch (e) { fail(main, e); }
}
