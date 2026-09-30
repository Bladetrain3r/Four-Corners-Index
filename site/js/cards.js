// Region price cards, mix cards and the drivers strip.
import { el, num, pct, monthLabel, periodLabel, convert, DIGITS, badge } from "./util.js";
import { sparkline } from "./charts.js";

const KIND = { household: "Household", industrial: "Industrial", wholesale: "Wholesale (day-ahead)" };

function priceRow(kind, c, cur, perEur, regionId) {
  const head = el("div", { class: "k" }, KIND[kind]);
  if (c.status === "gap") {
    return el("div", { class: "row gap", "data-testid": `${regionId}-${kind}`, "data-status": "gap" }, head, el("div", { class: "v" }, "No source"), el("div", { class: "meta" }, c.reason));
  }
  const v = convert(c.value, c.currency, cur, perEur);
  const native = c.currency === cur ? null : ` (${num(c.value, DIGITS[c.currency] ?? 3)} ${c.currency})`;
  const period = c.period_end.slice(0, 4) === "2026" && c.note.startsWith("An administrative") ? `in force since ${c.period_start}` : periodLabel(c.period_start, c.period_end);
  return el("div", { class: "row", "data-testid": `${regionId}-${kind}`, "data-status": "value" }, head,
    el("div", { class: "v" }, num(v, DIGITS[cur]), " ", el("small", {}, `${cur}/kWh${native || ""}`)),
    el("div", { class: "meta" }, `${period} · as of ${c.as_of}`, c.provisional ? " · preliminary" : "", c.confidence === "low_confidence" ? " · ⚠ low confidence" : ""),
    el("div", { class: "meta" }, el("a", { href: c.url }, c.source)),
    c.note ? el("div", { class: "meta" }, c.note) : null);
}

export function priceCards(regions, cur, perEur) {
  return regions.regions.map((r) => el("section", { class: "card region", "aria-label": `${r.name} prices`, "data-testid": `price-${r.id}` },
    el("h3", {}, el("span", {}, r.name), badge(r.badge)),
    el("p", { class: "meta" }, r.in_basket ? "In the index basket." : "Beside the basket, not in it.", " ", r.badge_note),
    ["household", "industrial", "wholesale"].map((k) => priceRow(k, r.cards[k], cur, perEur, r.id)),
    el("p", { class: "meta" }, el("a", { href: `region.html?r=${r.id}` }, "Long series, mix over time and sources →"))));
}

export function stackBar(mix, ariaName) {
  const segs = mix.fuels.filter((f) => mix.shares[f.id] > 0);
  const bar = el("div", { class: "stackbar", role: "img", "aria-label": `${ariaName} generation mix: ` + segs.map((f) => `${f.label} ${num(mix.shares[f.id] * 100, 0)}%`).join(", ") },
    segs.map((f) => el("span", { style: `flex:${mix.shares[f.id]};background:var(--series-${mix.fuels.findIndex((x) => x.id === f.id) + 1})`, title: `${f.label} ${num(mix.shares[f.id] * 100, 1)}%` })));
  const legend = el("ul", { class: "legend" }, segs.map((f) => el("li", {}, el("span", { class: "swatch", style: `background:var(--series-${mix.fuels.findIndex((x) => x.id === f.id) + 1})` }), `${f.label} ${num(mix.shares[f.id] * 100, 0)}%`)));
  return [bar, legend];
}

export function mixCards(regions) {
  return regions.regions.map((r) => {
    const m = r.mix;
    return el("section", { class: "card region", "aria-label": `${r.name} generation mix`, "data-testid": `mix-${r.id}` },
      el("h3", {}, el("span", {}, r.name), badge(r.badge, m.confidence === "low_confidence")),
      stackBar(m, r.name),
      el("p", { class: "carbon", "data-testid": `carbon-${r.id}` }, num(m.carbon, 0), " ", el("small", {}, "gCO₂ per kWh generated")),
      el("p", { class: "meta" }, `${monthLabel(m.m)} · ${num(m.total_twh, 0)} TWh generated · data as of ${m.as_of}`),
      el("p", { class: "meta" }, el("a", { href: m.url }, m.source)));
  });
}

export function driversStrip(d) {
  const notes = d.items.filter((i) => i.status === "gap");
  const sparks = d.items.filter((i) => i.status === "value").map((i) => {
    const host = el("div");
    sparkline(host, i.series, `${i.label}, last 12 months, latest ${num(i.latest.v, 2)} ${i.unit}`);
    return el("div", { class: "card spark", "data-testid": `driver-${i.id}` }, el("p", { class: "name" }, i.label),
      el("p", { class: "val" }, num(i.latest.v, 2), " ", el("small", { class: "muted" }, i.unit)),
      host,
      el("p", { class: "meta" }, `${pct(i.change_12m)} in 12 months · ${monthLabel(i.latest.m)} · as of ${i.as_of}`),
      el("p", { class: "meta" }, i.source, " ", badge(i.badge)));
  });
  return [el("div", { class: "sparks" }, sparks), notes.map((n) => el("p", { class: "notice", "data-testid": `driver-${n.id}` }, el("strong", {}, `${n.label}: no source. `), n.reason))];
}
