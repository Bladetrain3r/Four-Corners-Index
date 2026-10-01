import { el, getJSON, fail, $, num, badge } from "./util.js";
import { initPage } from "./layout.js";
import { chartCard } from "./charts.js";

const COLOR = { EU: 1, US: 2, CN: 3, GB: 4, RU: 5, ZA: 6 };  // the same slots the region charts use; Russia and South Africa take the next two
const pct0 = (x) => `${num(x * 100, 0)}%`;

const { main, src, error } = await initPage("air");
$("#loading")?.remove();

if (error) fail(main, error);
else {
  try {
    const d = await getJSON("data/air.json");
    main.append(el("p", { class: "lede" }, "How much fine particle pollution (PM2.5) the people of each region breathe in a year, next to the WHO guideline and what each region burns to make electricity. Annual, modelled and years late: a comparison, not an index."));
    main.append(el("div", { class: "notice", "data-testid": "air-method" }, el("strong", {}, "What this is and is not. "), d.method.map((t) => el("p", { class: "meta", style: "margin:.4em 0" }, t))));
    if (d.status !== "value") {
      main.append(el("div", { class: "notice", role: "status", "data-testid": "air-not-yet" }, el("strong", {}, "No data yet. "), d.reason));
    } else {
      const g = d.guideline;
      const ordered = [...d.regions].sort((a, b) => b.latest.value - a.latest.value);
      main.append(el("h2", { text: "Latest value per region" }),
        el("p", { class: "meta" }, `${d.indicator.label} (${d.indicator.unit}). ${g.label}: ${g.value} ${g.unit}. `, el("a", { href: g.url }, g.source), ". ", d.badge_note),
        el("div", { class: "grid", id: "air-cards" }, ordered.map((r) => el("section", { class: "card region", "data-testid": `air-${r.id}`, "aria-label": `${r.name} PM2.5` },
          el("h3", {}, el("span", {}, r.name), badge(d.badge)),
          el("div", { class: "row" }, el("div", { class: "k" }, `Mean annual exposure, ${r.latest.year}`),
            el("div", { class: "v", "data-testid": `air-${r.id}-value` }, num(r.latest.value, 1), " ", el("small", {}, d.indicator.unit)),
            el("div", { class: "meta" }, `${num(r.latest.times_guideline, 1)} × the WHO guideline`),
            el("div", { class: "meta" }, `Data as of ${d.as_of} · fetched ${d.retrieved}`),
            el("div", { class: "meta" }, el("a", { href: d.indicator.url }, "World Bank WDI, from IHME GBD 2023"), " · ", d.indicator.licence_line)),
          r.note ? el("p", { class: "meta" }, r.note) : null))));

      const xs = [...new Set(d.regions.flatMap((r) => r.series.map((p) => String(p.y))))].sort();
      const series = d.regions.map((r) => ({ id: r.id, label: r.name, short: r.short, color: `var(--series-${COLOR[r.id]})`, width: 2.2, values: xs.map((x) => (r.series.find((p) => String(p.y) === x) || {}).v ?? null) }));
      series.push({ id: "who", label: g.label, short: "WHO", color: "var(--text-primary)", dashed: true, width: 1.6, values: xs.map(() => g.value) });
      const fmt = (v) => num(v, 1);
      const c = chartCard({ title: `Mean annual PM2.5 exposure (${d.indicator.unit}), ${xs[0]} to ${xs[xs.length - 1]}`, desc: `Annual PM2.5 exposure for six regions from ${xs[0]} to ${xs[xs.length - 1]}, with the WHO 2021 guideline of ${g.value} micrograms per cubic metre as a dashed line.`,
        xs, yFmt: fmt, vFmt: fmt, zero: true, height: 300, series }, d.gap_note);
      main.append(el("h2", { text: "Since 1990" }), c.card);
      c.mount();

      const rows = ordered.map((r) => el("tr", { "data-testid": `air-row-${r.id}` }, el("th", { scope: "row" }, r.name), el("td", {}, num(r.latest.value, 1)), el("td", {}, `${num(r.latest.times_guideline, 1)} ×`), el("td", {}, r.mix ? pct0(r.mix.coal) : "n/a"),
        el("td", {}, r.mix ? pct0(r.mix.gas) : "n/a"), el("td", {}, r.mix ? pct0(r.mix.other_fossil) : "n/a"), el("td", {}, r.mix ? pct0(r.mix.clean) : "n/a"), el("td", {}, String(r.latest.year))));
      main.append(el("h2", { text: "What each region burns, beside it" }),
        el("p", { class: "meta" }, d.mix_note, " Clean means nuclear, hydro, wind, solar and bioenergy. A region's fuel shares are not its pollution: the two are shown together to compare, not to explain."),
        el("div", { class: "datatable full", tabindex: "0", role: "region", "aria-label": "PM2.5 and generation mix by region" },
          el("table", {}, el("thead", {}, el("tr", {}, ["Region", `PM2.5 (${d.indicator.unit})`, "× WHO guideline", "Coal", "Gas", "Other fossil", "Clean", "Year"].map((h) => el("th", { scope: "col" }, h)))), el("tbody", {}, rows))),
        el("h2", { text: "Source and licence" }),
        el("p", {}, d.indicator.source_note),
        el("p", { class: "meta" }, `${d.indicator.definition} `, el("a", { href: "sources.html#worldbank" }, "Licence, attribution and what we change.")),
        el("p", { class: "meta", "data-testid": "air-guideline-note" }, `Guideline: ${g.verification}`));
    }
  } catch (e) { fail(main, e); }
}
