// A small dependency-free SVG chart module: line and stacked-area charts on a shared monthly grid, annual stacked columns, sparklines.
// Every chart has a hover crosshair and tooltip, keyboard navigation (arrow keys, Home, End), an announced value, and a table alternative.
import { el, num } from "./util.js";

const NS = "http://www.w3.org/2000/svg";
const S = (tag, attrs = {}, parent) => {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.append(n);
  return n;
};
export const color = (i) => `var(--series-${(i % 8) + 1})`;

export function niceTicks(lo, hi, n = 5) {
  if (!(hi > lo)) { hi = lo + 1; }
  const raw = (hi - lo) / n;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw) || 10 * p;
  const a = Math.floor(lo / step) * step;
  const b = Math.ceil(hi / step) * step;
  const ticks = [];
  for (let v = a; v <= b + step / 2; v += step) ticks.push(Math.round(v / step) * step);
  return ticks;
}

function spread(labels, minGap, maxY = Infinity) {
  const s = labels.slice().sort((a, b) => a.y - b.y);
  for (let i = 1; i < s.length; i++) if (s[i].y - s[i - 1].y < minGap) s[i].y = s[i - 1].y + minGap;
  if (s.length && s[s.length - 1].y > maxY) {  // never run into the axis labels: push the stack back up from the bottom
    s[s.length - 1].y = maxY;
    for (let i = s.length - 2; i >= 0; i--) if (s[i + 1].y - s[i].y < minGap) s[i].y = s[i + 1].y - minGap;
  }
  return s;
}

/* spec: { title, desc, xs:['YYYY-MM',...], series:[{id,label,values:[n|null],color,dashed,labels:[str]}], stacked:false, yFmt, xTable,
           yMin,yMax,zero, height, shade:{from,label}, direct:true, unit } */
export function mount(host, spec, opts = {}) {
  host.classList.add("chart");
  host.setAttribute("tabindex", "0");
  host.setAttribute("role", "group");
  host.setAttribute("aria-label", `${spec.title}. Use the left and right arrow keys to read values.`);
  const live = el("div", { class: "sr", "aria-live": "polite" });
  Object.assign(live.style, { position: "absolute", width: "1px", height: "1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" });
  const tip = el("div", { class: "tip", role: "presentation", hidden: true });
  let cur = -1;
  let svg;

  function draw() {
    const w = Math.max(host.clientWidth, 260);
    if (!w) return;
    const h = spec.height || (w < 520 ? 230 : 290);
    const m = { l: 50, r: 10, t: 10, b: 24 };
    const n = spec.xs.length;
    const xs = (i) => m.l + (n === 1 ? 0 : (i / (n - 1)) * (w - m.l - m.r));
    let lo = Infinity, hi = -Infinity;
    const stackTops = [];
    if (spec.stacked) {
      for (let i = 0; i < n; i++) {
        let acc = 0;
        for (const s of spec.series) acc += s.values[i] ?? 0;
        stackTops.push(acc);
        hi = Math.max(hi, acc);
      }
      lo = 0;
    } else {
      for (const s of spec.series) for (const v of s.values) if (v !== null && v !== undefined) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
      if (spec.zero) lo = Math.min(lo, 0);
    }
    if (spec.yMin !== undefined) lo = spec.yMin;
    if (spec.yMax !== undefined) hi = spec.yMax;
    const ticks = niceTicks(lo, hi === lo ? hi + 1 : hi, w < 520 ? 4 : 5);
    const y0 = spec.stacked || spec.zero ? Math.min(ticks[0], 0) : ticks[0];
    const y1 = ticks[ticks.length - 1];
    const ys = (v) => m.t + (1 - (v - y0) / (y1 - y0)) * (h - m.t - m.b);

    svg?.remove();
    svg = S("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img", "aria-label": spec.desc || spec.title });
    S("title", {}, svg).textContent = spec.title;
    if (spec.shade) {
      const i0 = spec.xs.indexOf(spec.shade.from);
      if (i0 >= 0) S("rect", { x: xs(i0), y: m.t, width: xs(n - 1) - xs(i0), height: h - m.t - m.b, fill: "var(--shade)" }, svg);
    }
    const axis = S("g", { class: "axis" }, svg);
    for (const t of ticks) {
      S("line", { x1: m.l, x2: w - m.r, y1: ys(t), y2: ys(t), class: "gridline" }, axis);
      const tx = S("text", { x: m.l - 6, y: ys(t) + 4, "text-anchor": "end" }, axis);
      tx.textContent = spec.yFmt ? spec.yFmt(t) : num(t, 2);
    }
    const annual = spec.xs[0].length === 4;
    if (annual) {
      const every = Math.max(w < 520 && n > 6 ? 2 : 1, Math.ceil((n * 40) / (w - m.l - m.r)));  // thin the labels so they never touch
      spec.xs.forEach((x, i) => { if (i % every === 0) S("text", { x: xs(i), y: h - 6, "text-anchor": "middle" }, axis).textContent = x; });
    } else {
      const firstYear = Number(spec.xs[0].slice(0, 4)), lastYear = Number(spec.xs[n - 1].slice(0, 4));
      const maxLabels = w < 520 ? 5 : 10;
      const step = Math.max(1, Math.ceil((lastYear - firstYear + 1) / maxLabels));
      spec.xs.forEach((x, i) => {
        const yr = Number(x.slice(0, 4));
        const atYearStart = x.length < 7 || x.slice(5, 7) === "01" || i === 0;
        if (atYearStart && (yr - firstYear) % step === 0 && (i === 0 || x.slice(5, 7) === "01" || x.length < 7)) {
          S("text", { x: xs(i), y: h - 6, "text-anchor": i === 0 ? "start" : "middle" }, axis).textContent = x.slice(0, 4);
        }
      });
    }

    if (spec.stacked && spec.columns) {  // annual stacked columns
      const bw = Math.max(6, Math.min(48, (w - m.l - m.r) / n * 0.62));
      spec.xs.forEach((_, i) => {
        let acc = 0;
        spec.series.forEach((s, k) => {
          const v = s.values[i] ?? 0;
          S("rect", { x: xs(i) - bw / 2, y: ys(acc + v), width: bw, height: Math.max(0, ys(acc) - ys(acc + v) - 1.5), fill: s.color || color(k), rx: 2 }, svg);
          acc += v;
        });
      });
      (spec.overlay || []).forEach((o) => {
        const pts = spec.xs.map((_, i) => (o.values[i] === null ? null : [xs(i), ys(o.values[i])]));
        pts.forEach((p) => { if (p) S("circle", { cx: p[0], cy: p[1], r: 4, fill: "var(--surface-1)", stroke: "var(--text-primary)", "stroke-width": 2 }, svg); });
      });
    } else if (spec.stacked) {
      let base = new Array(n).fill(0);
      spec.series.forEach((s, k) => {
        const top = base.map((b, i) => b + (s.values[i] ?? 0));
        const d = top.map((v, i) => `${i ? "L" : "M"}${xs(i)},${ys(v)}`).join("") + base.map((b, i) => `L${xs(n - 1 - i)},${ys(base[n - 1 - i])}`).join("") + "Z";
        S("path", { d, fill: s.color || color(k), stroke: "var(--surface-1)", "stroke-width": 1.5, "stroke-linejoin": "round" }, svg);
        base = top;
      });
    } else {
      spec.series.forEach((s, k) => {
        let d = "";
        let pen = false;
        s.values.forEach((v, i) => {
          if (v === null || v === undefined) { pen = false; return; }
          d += `${pen ? "L" : "M"}${xs(i)},${ys(v)}`;
          pen = true;
        });
        S("path", { d, fill: "none", stroke: s.color || color(k), "stroke-width": s.width || 2, "stroke-linejoin": "round", "stroke-dasharray": s.dashed ? "6 4" : "none" }, svg);
      });
      if (spec.direct !== false) {  // direct labels at the right end, never a number on every point
        const labs = spec.series.map((s) => {
          let i = s.values.length - 1;
          while (i > 0 && (s.values[i] === null || s.values[i] === undefined)) i--;
          return { y: ys(s.values[i]), text: `${s.short || s.label} ${spec.yFmt ? spec.yFmt(s.values[i]) : num(s.values[i], 3)}`, i };
        });
        const placed = spread(labs, 18, h - m.b - 2);
        placed.forEach((l) => {
          const t = S("text", { x: w - m.r, y: l.y - 4, "text-anchor": "end", style: "fill:var(--text-primary);font-size:11px", stroke: "var(--surface-1)", "stroke-width": 3, "paint-order": "stroke" }, svg);
          t.textContent = l.text;
        });
      }
    }
    if (spec.shade) {
      const i0 = spec.xs.indexOf(spec.shade.from);
      if (i0 >= 0) { const t = S("text", { x: xs(i0) + 4, y: m.t + 11, style: "fill:var(--text-secondary);font-size:11px" }, svg); t.textContent = spec.shade.label; }
    }
    const cross = S("line", { y1: m.t, y2: h - m.b, stroke: "var(--text-secondary)", "stroke-width": 1, visibility: "hidden" }, svg);
    const dots = spec.series.map((s, k) => S("circle", { r: 4, fill: s.color || color(k), stroke: "var(--surface-1)", "stroke-width": 2, visibility: "hidden" }, svg));
    const overlay = S("rect", { x: m.l, y: m.t, width: w - m.l - m.r, height: h - m.t - m.b, fill: "transparent" }, svg);
    host.replaceChildren(svg, tip, live);
    svg.__geo = { xs, ys, m, w, h, n };

    function show(i, fromPointer) {
      if (i < 0 || i >= n) return;
      cur = i;
      const x = xs(i);
      cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("visibility", "visible");
      const rows = [];
      let acc = 0;
      spec.series.forEach((s, k) => {
        const v = s.values[i];
        if (spec.stacked) acc += v ?? 0;
        const yv = spec.stacked ? acc : v;
        if (!spec.columns && v !== null && v !== undefined) { dots[k].setAttribute("cx", x); dots[k].setAttribute("cy", ys(yv)); dots[k].setAttribute("visibility", "visible"); } else dots[k].setAttribute("visibility", "hidden");
        rows.push({ s, k, v, label: s.labels ? s.labels[i] : "" });
      });
      tip.hidden = false;
      const title = spec.xLabel ? spec.xLabel(spec.xs[i]) : spec.xs[i];
      tip.replaceChildren(el("div", { class: "t" }, title), ...rows.map((r) => el("div", { class: "r" }, el("span", {}, el("span", { class: "swatch", style: `background:${r.s.color || color(r.k)}` }), " ", r.s.short || r.s.label), el("b", {}, r.v === null || r.v === undefined ? (spec.gapText || "no data") : (spec.vFmt ? spec.vFmt(r.v) : num(r.v, 3)) + (r.label ? ` (${r.label})` : "")))));
      const tw = tip.offsetWidth || 160;
      tip.style.left = Math.max(0, Math.min(w - tw, x + 12 > w - tw ? x - tw - 12 : x + 12)) + "px";
      tip.style.top = (fromPointer ? 8 : 12) + "px";
      live.textContent = `${title}: ` + rows.map((r) => `${r.s.label} ${r.v === null || r.v === undefined ? "no data" : (spec.vFmt ? spec.vFmt(r.v) : num(r.v, 3))}`).join(", ");
    }
    function hide() { cross.setAttribute("visibility", "hidden"); dots.forEach((d) => d.setAttribute("visibility", "hidden")); tip.hidden = true; }
    overlay.addEventListener("pointermove", (ev) => {
      const r = svg.getBoundingClientRect();
      const px = ((ev.clientX - r.left) / r.width) * w;
      show(Math.max(0, Math.min(n - 1, Math.round(((px - m.l) / (w - m.l - m.r)) * (n - 1)))), true);
    });
    overlay.addEventListener("pointerleave", () => { if (document.activeElement !== host) hide(); });
    host.onkeydown = (ev) => {
      const k = ev.key;
      if (k === "ArrowLeft" || k === "ArrowRight" || k === "Home" || k === "End") {
        ev.preventDefault();
        const next = k === "Home" ? 0 : k === "End" ? n - 1 : Math.max(0, Math.min(n - 1, (cur < 0 ? n - 1 : cur) + (k === "ArrowRight" ? 1 : -1)));
        show(next, false);
      } else if (k === "Escape") hide();
    };
    host.onblur = hide;
    if (cur >= 0 && document.activeElement === host) show(cur, false);
  }

  draw();
  let t;
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => { clearTimeout(t); t = setTimeout(draw, 80); }) : null;
  ro?.observe(host);
  return { redraw: (next) => { if (next) spec = next; cur = -1; draw(); }, table: () => dataTable(spec), destroy: () => ro?.disconnect() };
}

export function dataTable(spec) {
  const fmt = spec.vFmt || ((v) => num(v, 3));
  const head = el("tr", {}, el("th", { scope: "col" }, spec.xHeader || "Period"), ...spec.series.map((s) => el("th", { scope: "col" }, s.label)));
  const body = spec.xs.map((x, i) => el("tr", {}, el("th", { scope: "row" }, spec.xLabel ? spec.xLabel(x) : x),
    ...spec.series.map((s) => el("td", {}, s.values[i] === null || s.values[i] === undefined ? (spec.gapText || "no data") : fmt(s.values[i]) + (s.labels && s.labels[i] ? ` (${s.labels[i]})` : "")))));
  return el("div", { class: "datatable", tabindex: "0", role: "region", "aria-label": `${spec.title}: data table` }, el("table", {}, el("caption", { class: "sr", style: "position:absolute;left:-999px" }, spec.title), el("thead", {}, head), el("tbody", {}, body)));
}

// A chart card: title, "View as table" toggle, the chart, an optional note.
export function chartCard(spec, note) {
  const host = el("div");
  const slot = el("div");
  const btn = el("button", { class: "tablebtn", type: "button", "aria-expanded": "false" }, "View as table");
  let handle;
  btn.addEventListener("click", () => {
    const open = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", String(!open));
    btn.textContent = open ? "View as table" : "Hide table";
    slot.replaceChildren(...(open ? [] : [handle.table()]));
  });
  const legend = el("ul", { class: "legend" });
  const fillLegend = () => legend.replaceChildren(...(spec.stacked ? spec.series.map((s, k) => el("li", {}, el("span", { class: "swatch", style: `background:${s.color || color(k)}` }), s.label)) : []));
  const card = el("section", { class: "card chartcard", "aria-label": spec.title }, el("div", { class: "head" }, el("h3", {}, spec.title), btn), note ? el("p", { class: "meta" }, note) : null, host, legend, slot);
  return { card, mount() { fillLegend(); handle = mount(host, spec); return handle; }, update(next) { spec = next; fillLegend(); handle.redraw(next); if (btn.getAttribute("aria-expanded") === "true") slot.replaceChildren(handle.table()); } };
}

export function sparkline(host, pts, label) {
  const w = 200, h = 44, pad = 4;
  const vals = pts.map((p) => p.v);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const sx = (i) => pad + (i / (pts.length - 1)) * (w - 2 * pad);
  const sy = (v) => pad + (1 - (hi === lo ? 0.5 : (v - lo) / (hi - lo))) * (h - 2 * pad);
  const svg = S("svg", { viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": label, preserveAspectRatio: "none" });
  S("polyline", { points: pts.map((p, i) => `${sx(i)},${sy(p.v)}`).join(" "), fill: "none", stroke: "var(--series-1)", "stroke-width": 2, "vector-effect": "non-scaling-stroke", "stroke-linejoin": "round" }, svg);
  S("circle", { cx: sx(pts.length - 1), cy: sy(vals[vals.length - 1]), r: 3.5, fill: "var(--series-1)", stroke: "var(--surface-1)", "stroke-width": 1.5 }, svg);
  host.replaceChildren(svg);
}
