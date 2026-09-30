import { el, getJSON, store, fail, $ } from "./util.js";
import { initPage } from "./layout.js";
import { retailTile, wholesaleTile, charts, VARIANTS } from "./tiles.js";
import { priceCards, mixCards, driversStrip } from "./cards.js";

function seg(legend, name, options, current, onChange) {
  const fs = el("fieldset", { class: "seg" }, el("legend", {}, legend));
  for (const [value, label] of options) {
    const input = el("input", { type: "radio", name, value, checked: value === current ? true : null });
    input.addEventListener("change", () => onChange(value));
    fs.append(el("label", {}, input, el("span", {}, label)));
  }
  return fs;
}

const { main, error } = await initPage("home");
$("#loading")?.remove();

if (error) fail(main, error);
else {
  try {
    const [idx, regions, drivers] = await Promise.all([getJSON("data/index.json"), getJSON("data/regions.json"), getJSON("data/drivers.json")]);
    const st = { cur: store.get("cur", "USD"), variant: store.get("variant", "weighted") };
    if (!["USD", "EUR", "ZAR"].includes(st.cur)) st.cur = "USD";
    if (!VARIANTS[st.variant]) st.variant = "weighted";

    const tiles = el("div", { class: "tiles", id: "tiles" });
    const chartsHost = el("div", { id: "charts" });
    const priceGrid = el("div", { class: "grid", id: "price-cards" });
    let handles = [];

    // Controls are built once so keyboard focus stays on the radio the user just used.
    const controls = el("div", { class: "controls", id: "controls", role: "group", "aria-label": "Display options" },
      seg("Currency", "cur", [["USD", "US dollar"], ["EUR", "Euro"], ["ZAR", "Rand"]], st.cur, (v) => { st.cur = v; store.set("cur", v); render(); }),
      seg("Retail weighting", "variant", Object.entries(VARIANTS).map(([k, [label]]) => [k, label]), st.variant, (v) => { st.variant = v; store.set("variant", v); render(); }),
      el("p", { class: "meta", style: "margin:0" }, "Levels convert at each month's ECB average rate; index numbers (2015 = 100) are in US-dollar terms."));

    function render() {
      tiles.replaceChildren(retailTile(idx, st.variant, st.cur), wholesaleTile(idx, st.cur));
      priceGrid.replaceChildren(...priceCards(regions, st.cur, regions.fx_latest.per_eur));
      handles.forEach((h) => h.destroy());
      const c = charts(idx, st.variant, st.cur);
      chartsHost.replaceChildren(c.retail.card, c.contrib.card, c.wholesale.card);
      handles = [c.retail.mount(), c.contrib.mount(), c.wholesale.mount()];
    }

    main.append(
      el("h2", { text: "The two indices" }), controls, tiles, chartsHost,
      el("h2", { text: "Prices by region: household, industrial, wholesale" }),
      el("p", { class: "lede" }, "Each figure carries its period, its source and the date the source published it. A missing figure is shown as missing, with the reason."), priceGrid,
      el("h2", { text: "What it is made of" }),
      el("p", { class: "lede" }, "Share of generation by source in the latest month, and carbon intensity. Ember does not separate oil from other fossil fuels, and “bioenergy and other renewables” are combined."),
      el("div", { class: "grid", id: "mix-cards" }, mixCards(regions)),
      el("h2", { text: "Why it moves: drivers" }),
      el("p", { class: "lede" }, "Twelve months of the main drivers. Gas and coal are nominal US dollars; exchange rates are ECB monthly averages."),
      el("div", { id: "drivers" }, driversStrip(drivers)));
    render();
    window.addEventListener("themechange", () => handles.forEach((h) => h.redraw()));
  } catch (e) {
    fail(main, e);
  }
}
