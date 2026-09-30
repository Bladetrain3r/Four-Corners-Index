import { el, getJSON, fail, $, num, monthLabel, DIGITS, badge } from "./util.js";
import { initPage } from "./layout.js";
import { chartCard, dataTable } from "./charts.js";
import { priceCards, stackBar } from "./cards.js";

const { main, src, meta, error } = await initPage("region");
$("#loading")?.remove();

// A semester or month step series onto a monthly grid: each month takes the value of the period that contains it.
function monthly(points, xs) {
  return xs.map((m) => {
    const d = m + "-01";
    const p = points.find((q) => q.s <= d && d <= q.e);
    return p ? p.v : null;
  });
}
const monthsFrom = (a, b) => { const out = []; for (let y = +a.slice(0, 4), mo = +a.slice(5); `${y}-${String(mo).padStart(2, "0")}` <= b; mo++) { if (mo > 12) { mo = 1; y++; } out.push(`${y}-${String(mo).padStart(2, "0")}`); } return out; };

if (error) fail(main, error);
else {
  try {
    const regions = await getJSON("data/regions.json");
    const id = (new URLSearchParams(location.search).get("r") || "EU").toUpperCase();
    const r = regions.regions.find((x) => x.id === id) || regions.regions[0];
    const d = await getJSON(`data/region_${r.id}.json`);
    document.title = `${r.name} - Four Corners Index`;
    main.querySelector("h1").textContent = r.name;
    main.querySelector("h1").after(el("nav", { class: "switch", "aria-label": "Regions" }, regions.regions.map((x) => el("a", { href: `region.html?r=${x.id}`, "aria-current": x.id === r.id ? "page" : null }, x.name))));
    main.append(el("p", { class: "lede" }, r.in_basket ? "In the index basket." : "Beside the basket, not in it.", " ", r.badge_note, " ", badge(r.badge)));
    main.append(el("div", { class: "grid", id: "region-prices" }, priceCards({ regions: [r] }, "USD", regions.fx_latest.per_eur)));

    const hs = d.household_usd_monthly || [];
    if (hs.length) {
      const xs = hs.map((p) => p.m);
      const fmt = (v) => num(v, 3);
      const carriedFrom = hs.find((p) => p.carried)?.m;
      const c = chartCard({ title: `${r.name}: household price (USD per kWh, monthly average FX)`, desc: `Household price in USD per kWh, ${monthLabel(xs[0])} to ${monthLabel(xs[xs.length - 1])}.`, xs, xLabel: monthLabel, yFmt: fmt, vFmt: fmt, zero: true, height: 260,
        shade: carriedFrom ? { from: carriedFrom, label: "carried forward" } : undefined,
        series: [{ id: "h", label: "Household", color: "var(--series-1)", width: 2.4, values: hs.map((p) => p.v) }] },
        "The local price converted at each month's ECB average rate. Semester and administrative prices apply to every month they cover; shaded months carry the last published value.");
      main.append(c.card); c.mount();
    }

    const entries = Object.entries(d.series);
    if (entries.length) {
      const xs = monthsFrom("2015-01", meta.latest.retail);
      const ser = entries.map(([k, s], i) => ({ id: k, label: s.label, short: k, color: `var(--series-${i + 1})`, dashed: k.endsWith("_comparison"), width: k.endsWith("_comparison") ? 1.6 : 2.4, values: monthly(s.points, xs) }));
      const cur = entries[0][1].currency;
      const fmt = (v) => num(v, DIGITS[cur] ?? 3);
      const c = chartCard({ title: `${r.name}: prices by buyer type (${cur} per kWh, as published)`, desc: `Household, industrial and wholesale prices in ${cur} per kWh, as published, with comparison series dashed.`, xs, xLabel: monthLabel, yFmt: fmt, vFmt: fmt, zero: true, direct: false, height: 280, series: ser },
        "In the currency the source publishes. Dashed lines are comparison series that are not in either index.");
      const legend = el("ul", { class: "legend" }, ser.map((s) => el("li", {}, el("span", { class: "swatch", style: `background:${s.color}` }), s.label)));
      main.append(c.card); c.mount(); c.card.querySelector(".chart").after(legend);
    }

    if (d.components) {
      const ys = d.components.years;
      const fmt = (v) => num(v, 4);
      const parts = [["energy_supply", "Energy and supply"], ["network", "Network"], ["other_taxes_levies", "Other taxes and levies"], ["vat", "VAT"]];
      const spec = { title: `${r.name}: what a household kWh pays for (${d.components.unit}, by year)`, desc: "Household price components by year: energy and supply, network, other taxes and levies, VAT.", xs: ys.map((y) => y.year), yFmt: fmt, vFmt: fmt, stacked: true, columns: true, height: 280,
        overlay: [{ values: d.components.reconciliation.map((x) => x.half_year_mean) }],
        series: parts.map(([k, l], i) => ({ id: k, label: l, color: `var(--series-${i + 1})`, values: ys.map((y) => y[k]) })) };
      const c = chartCard(spec, d.components.note);
      main.append(c.card); c.mount();
      main.append(el("h3", { text: "Do the components add up to the headline series?" }),
        el("p", { class: "meta" }, "Circles above are the mean of the two half-year headline values (band DC, all taxes). The components are annual and from a different Eurostat table, so they differ a little, in both directions. Published as measured:"),
        el("div", { class: "datatable full", tabindex: "0", role: "region", "aria-label": "Component reconciliation" }, el("table", {}, el("thead", {}, el("tr", {}, ["Year", "Components total", "Half-year mean", "Difference"].map((h) => el("th", { scope: "col" }, h)))),
          el("tbody", {}, d.components.reconciliation.map((x) => el("tr", {}, el("th", { scope: "row" }, x.year), el("td", {}, num(x.components_total, 4)), el("td", {}, num(x.half_year_mean, 4)), el("td", {}, `${x.difference >= 0 ? "+" : "−"}${num(Math.abs(x.difference), 4)} (${num((x.difference / x.half_year_mean) * 100, 1)}%)`)))))));
    }

    if (d.mix_over_time.length) {
      const mx = d.mix_over_time;
      const fuels = r.mix.fuels;
      const spec = { title: `${r.name}: generation mix over time (share of generation)`, desc: "Share of generation by fuel, monthly.", xs: mx.map((p) => p.m), xLabel: monthLabel, stacked: true, yMax: 1, height: 280,
        yFmt: (v) => `${num(v * 100, 0)}%`, vFmt: (v) => `${num(v * 100, 1)}%`,
        series: fuels.map((f, i) => ({ id: f.id, label: f.label, color: `var(--series-${i + 1})`, values: mx.map((p) => p.shares[f.id] ?? 0) })) };
      const c = chartCard(spec, `Ember Monthly Electricity Data. ${r.mix.confidence === "low_confidence" ? "Low confidence: Ember's estimate. " : ""}Carbon intensity, latest month: ${num(r.mix.carbon, 0)} gCO₂ per kWh generated.`);
      main.append(c.card); c.mount();
    }

    main.append(el("h2", { text: "Sources for this region" }), el("ul", { id: "region-sources" }, d.sources.map((sid) => {
      const s = src.used.find((u) => u.id === sid);
      return el("li", {}, s ? [el("a", { href: `sources.html#${s.id}` }, s.name), ": ", s.attribution] : sid);
    })));
  } catch (e) { fail(main, e); }
}
