// The two headline tiles and the index charts.
import { el, num, pct, monthLabel, addMonths, levelIn, money, shortMoney, badge, statusChip, DIGITS } from "./util.js";
import { chartCard } from "./charts.js";

export const VARIANTS = { weighted: ["Weighted (headline)", "level", "index"], equal: ["Equal-weighted", "equal_level", "equal_index"], exchina: ["Excluding China", "ex_level", "ex_index"] };
const REG = [["EU", "EU", 0], ["US", "US", 1], ["CN", "China", 2], ["GB", "UK", 3]];
const REGION_NAME = { EU: "EU", US: "US", CN: "China", GB: "UK", RU: "Russia" };

const byMonth = (rows) => Object.fromEntries(rows.map((r) => [r.m, r]));
export const fxOf = (idx, m) => idx.fx[m];

export function values(rows, idx, key, cur) {
  const map = byMonth(rows);
  const last = rows[rows.length - 1];
  const at = (m) => (map[m] ? levelIn(map[m][key], cur, fxOf(idx, m)) : null);
  const now = at(last.m);
  const prev = at(addMonths(last.m, -1));
  const year = at(addMonths(last.m, -12));
  return { last, now, mom: prev ? now / prev - 1 : null, yoy: year ? now / year - 1 : null };
}

function tile({ id, title, rows, idx, variant, cur, sourceText, composition, quality, qualityNote, extra }) {
  const [vlabel, lk, ik] = VARIANTS[variant];
  const v = values(rows, idx, lk, cur);
  const r = v.last;
  const isVariant = variant !== "weighted";
  return el("section", { class: "card tile", "aria-labelledby": `${id}-h`, "data-testid": id }, 
    el("p", { class: "label", id: `${id}-h` }, title + (isVariant ? ` — ${vlabel.toLowerCase()} variant (not the headline)` : "")),
    el("p", { class: "big", "data-testid": `${id}-value` }, shortMoney(v.now, cur), " ", el("small", {}, `${cur}/kWh`)),
    el("div", { class: "kv" }, el("span", {}, "Index (2015 = 100): ", el("b", { "data-testid": `${id}-index` }, num(r[ik], 1))),
      el("span", {}, "Month on month: ", el("b", { "data-testid": `${id}-mom` }, pct(v.mom))), el("span", {}, "Year on year: ", el("b", { "data-testid": `${id}-yoy` }, pct(v.yoy)))),
    el("div", { class: "kv" }, statusChip(r.status), el("span", {}, "Month: ", el("b", {}, monthLabel(r.m))), el("span", {}, "Published: ", el("b", {}, r.published))),
    extra || null,
    el("p", { class: "source", "data-testid": `${id}-source` }, el("strong", {}, "Source: "), sourceText),
    el("p", { class: "source" }, el("strong", {}, "Composition: "), composition),
    el("p", { class: "source", "data-testid": `${id}-badge` }, badge(quality), " ", qualityNote),
    el("p", { class: "source" }, el("a", { href: "indices.html" }, "Weights, variants and revisions"), " · ", el("a", { href: "method.html" }, "Method")));
}

export function retailTile(idx, variant, cur) {
  const rows = idx.retail;
  const last = rows[rows.length - 1];
  const list = Object.entries(VARIANTS).map(([k, [label, lk]]) => {
    const v = values(rows, idx, lk, cur);
    return el("div", { "aria-current": k === variant ? "true" : null, style: k === variant ? "font-weight:650" : "" }, el("span", {}, label), el("span", {}, `${shortMoney(v.now, cur)} ${cur}/kWh · index ${num(last[VARIANTS[k][2]], 1)}`));
  });
  return tile({ id: "retail", title: "Retail index: what households pay", rows, idx, variant, cur,
    sourceText: "Eurostat (EU), U.S. EIA (US), Shanghai DRC notice (China), DESNZ (UK); ECB exchange rates; weights from Ember.",
    composition: `${last.composition.map((c) => REGION_NAME[c]).join(", ")}. Russia has no price source, so weights are renormalised.`,
    quality: "C", qualityNote: "Weakest region: China (one administrative tariff, low confidence). EU, US and UK are A.", extra: el("div", { class: "variants", "data-testid": "retail-variants" }, list) });
}

export function wholesaleTile(idx, cur) {
  const rows = idx.wholesale;
  const last = rows[rows.length - 1];
  const c = idx.wholesale_composition[last.m];
  return tile({ id: "wholesale", title: "Wholesale index: EU day-ahead price", rows, idx, variant: "weighted", cur,
    sourceText: "Ember European wholesale prices (from ENTSO-E), Eurostat inland demand for weights, ECB exchange rates.",
    composition: `EU only: ${c.n} member states with a price, ${num(c.share * 100, 1)}% of EU inland demand. No other region has a reusable wholesale feed.`,
    quality: "A", qualityNote: "Official market data via Ember (CC-BY)." });
}

const seriesOf = (rows, key, idx, cur) => rows.map((r) => levelIn(r[key], cur, fxOf(idx, r.m)));

export function retailChartSpec(idx, variant, cur) {
  const rows = idx.retail;
  const fmt = (v) => num(v, DIGITS[cur]);
  const mk = (k, label, colr, dashed) => ({ id: k, label, short: label.split(" (")[0], color: colr, dashed, width: variant === k ? 3.2 : 1.8, values: seriesOf(rows, VARIANTS[k][1], idx, cur) });
  return { title: `Retail index level (${cur} per kWh, nominal)`, desc: `Retail index in ${cur} per kWh from ${monthLabel(rows[0].m)} to ${monthLabel(rows[rows.length - 1].m)}: weighted headline, equal-weighted and excluding China.`,
    xs: rows.map((r) => r.m), xLabel: monthLabel, series: [mk("weighted", "Weighted (headline)", "var(--text-primary)"), mk("equal", "Equal-weighted", "var(--series-5)"), mk("exchina", "Excluding China", "var(--series-6)", true)],
    yFmt: fmt, vFmt: fmt, shade: { from: rows.find((r) => r.status === "provisional")?.m, label: "provisional" }, height: 300 };
}

export function contribSpec(idx, variant, cur) {
  const rows = idx.retail;
  const fmt = (v) => num(v, DIGITS[cur]);
  let regs = REG, get;
  if (variant === "exchina") { regs = REG.filter((r) => r[0] !== "CN"); get = (r, g) => r.ex_contrib[g]; }
  else if (variant === "equal") get = (r, g) => (r.contrib[g] / r.weights[g]) / Object.keys(r.contrib).length;
  else get = (r, g) => r.contrib[g];
  const label = variant === "exchina" ? "excluding China" : variant === "equal" ? "equal-weighted" : "weighted";
  return { title: `Retail index by region, ${label} (weight × price, ${cur} per kWh; the regions add up to the level)`, desc: `Stacked contribution of each region to the ${label} retail index.`, stacked: true,
    xs: rows.map((r) => r.m), xLabel: monthLabel, yFmt: fmt, vFmt: fmt, height: 280, shade: { from: rows.find((r) => r.status === "provisional")?.m, label: "provisional" },
    series: regs.map(([g, name, k]) => ({ id: g, label: name, color: `var(--series-${k + 1})`, values: rows.map((r) => levelIn(get(r, g), cur, fxOf(idx, r.m))) })) };
}

export function wholesaleSpec(idx, cur) {
  const rows = idx.wholesale;
  const fmt = (v) => num(v, DIGITS[cur]);
  return { title: `EU wholesale index level (${cur} per kWh, nominal)`, desc: `EU day-ahead wholesale price in ${cur} per kWh from ${monthLabel(rows[0].m)} to ${monthLabel(rows[rows.length - 1].m)}.`,
    xs: rows.map((r) => r.m), xLabel: monthLabel, yFmt: fmt, vFmt: fmt, zero: true, height: 280,
    series: [{ id: "w", label: "EU wholesale", color: "var(--text-primary)", width: 2.4, values: seriesOf(rows, "level", idx, cur) }] };
}

export function charts(idx, variant, cur) {
  return { retail: chartCard(retailChartSpec(idx, variant, cur), "Weighted headline in bold (ink); the equal-weighted and excluding-China variants beside it. Shaded months are provisional."),
    contrib: chartCard(contribSpec(idx, variant, cur), "Russia is in the weights but has no price, so it is not drawn; the UK's share is small because its demand is small."),
    wholesale: chartCard(wholesaleSpec(idx, cur), "EU only. Before mid-2016 fewer countries have a price; the composition is on the indices page.") };
}
