import { el, getJSON, fail, $, num, monthLabel, DIGITS } from "./util.js";
import { initPage } from "./layout.js";
import { chartCard } from "./charts.js";
import { retailChartSpec, contribSpec, wholesaleSpec } from "./tiles.js";

const { main, meta, error } = await initPage("indices");
$("#loading")?.remove();

function revisionSummary(revs) {
  const first = revs.length ? revs[0].published : "";
  const restated = revs.filter((r) => r.published === first);
  const later = revs.filter((r) => r.published !== first);
  const statusOnly = later.filter((r) => Number(r.from) === Number(r.to)).length;
  let t = `Revisions so far: ${revs.length}. ${restated.length} restate every Retail month when the UK joined (METHOD version 3, ${first}).`;
  if (later.length) t += ` ${later.length} later: ${statusOnly} where a month turned final at the same value (its last provisional input aged out), ${later.length - statusOnly} where the value changed.`;
  return t;
}

const table = (label, head, rows, cls = "") => el("div", { class: `datatable ${cls}`, tabindex: "0", role: "region", "aria-label": label },
  el("table", {}, el("thead", {}, el("tr", {}, head.map((h) => el("th", { scope: "col" }, h)))), el("tbody", {}, rows)));

if (error) fail(main, error);
else {
  try {
    const idx = await getJSON("data/index.json");
    const mv = meta.headline_method_version;
    main.append(
      el("p", { class: "lede" }, `Retail is a consumption-weighted average of household prices in the EU, US, China and the UK (Russia is in the weights but has no price source). Wholesale is the EU day-ahead price only. Both are nominal US dollars per kWh, monthly from 2015, with 2015 = 100 beside the level. Headline method versions: Retail ${mv.retail}, Wholesale ${mv.wholesale}; the method document is version ${meta.method_doc_version}. `,
        el("a", { href: "method.html" }, "Read the method.")));

    // Weights
    const years = [...new Set(idx.weights.map((w) => w.year))].sort();
    const regs = ["EU", "US", "CN", "RU", "GB"];
    const by = (y, r) => idx.weights.find((w) => w.year === y && w.region === r);
    main.append(el("h2", { text: "Weights by year" }),
      el("p", { class: "meta" }, "Share of Ember's yearly electricity demand of the previous year among the five basket regions. Russia is in the denominator; the right-hand columns are renormalised over the regions that have a price."),
      table("Weights by year", ["Year", ...regs.map((r) => `${r} share`), "EU · US · CN · GB (renormalised)"],
        years.map((y) => el("tr", {}, el("th", { scope: "row" }, y), ...regs.map((r) => el("td", {}, by(y, r) ? `${num(by(y, r).share_of_five * 100, 1)}%` : "n/a")),
          el("td", {}, ["EU", "US", "CN", "GB"].map((r) => (by(y, r) && by(y, r).share_retail !== null && by(y, r).share_retail !== undefined ? `${num(by(y, r).share_retail * 100, 1)}%` : "n/a")).join(" · ")))), "full"));

    // Variants and contributions
    main.append(el("h2", { text: "Retail variants and contributions" }),
      el("p", { class: "meta" }, "The headline is weighted. The equal-weighted variant gives each included region the same weight; it is dominated by the UK's 2022 to 2023 household spike. Excluding China shows the part of the index that rests on measured prices rather than one administrative tariff."));
    const cards = [chartCard(retailChartSpec(idx, "weighted", "USD"), "USD per kWh, nominal. Shaded months are provisional."),
      chartCard(contribSpec(idx, "weighted", "USD"), "Headline: regions add up to the level."),
      chartCard(contribSpec(idx, "exchina", "USD"), "Excluding China: EU, US and UK renormalised."),
      chartCard(wholesaleSpec(idx, "USD"), "EU day-ahead, demand-weighted.")];
    main.append(...cards.map((c) => c.card));
    cards.forEach((c) => c.mount());

    // Wholesale composition
    const comp = Object.entries(idx.wholesale_composition).sort();
    const last = comp[comp.length - 1];
    const cc = chartCard({ title: "EU wholesale: countries with a price and share of EU demand covered", desc: "Number of EU countries in the wholesale index per month.", xs: comp.map(([m]) => m), xLabel: monthLabel, yFmt: (v) => num(v, 0), vFmt: (v) => num(v, 0), zero: true, height: 220, series: [{ id: "n", label: "Countries", color: "var(--series-1)", width: 2.4, values: comp.map(([, c]) => c.n) }, { id: "s", label: "Share of EU inland demand (%)", color: "var(--series-2)", values: comp.map(([, c]) => Math.round(c.share * 1000) / 10) }] },
      `Latest month ${monthLabel(last[0])}: ${last[1].n} countries (${last[1].countries.join(", ")}), covering ${num(last[1].share * 100, 1)}% of EU inland demand. Cyprus and Malta have no price; Bulgaria, Croatia and Ireland start later.`);
    main.append(el("h2", { text: "Wholesale composition" }), cc.card); cc.mount();

    // Ledger and revisions
    main.append(el("h2", { text: "Revision ledger" }),
      el("p", {}, `${idx.ledger.lines} ledger lines, hash-chained; head ${idx.ledger.head.slice(0, 16)}… A revision is a new line that names the line it supersedes; nothing is edited. Check it with `, el("code", {}, "python ledger/verify.py ledger/index.jsonl"), ". ", el("a", { href: "downloads.html" }, "Download the ledger.")),
      el("p", { class: "meta", "data-testid": "revisions-summary" }, revisionSummary(idx.revisions)),
      table("Revisions", ["Index", "Month", "Was", "Now", "Status", "Published", "Line"],
        idx.revisions.map((r) => el("tr", {}, el("th", { scope: "row" }, r.index), el("td", {}, monthLabel(r.month)), el("td", {}, num(+r.from, 4)), el("td", {}, num(+r.to, 4)), el("td", {}, r.from_status === r.to_status ? r.to_status : `${r.from_status} → ${r.to_status}`), el("td", {}, r.published), el("td", {}, el("code", {}, r.hash)))), "tablewide"));
  } catch (e) { fail(main, e); }
}
