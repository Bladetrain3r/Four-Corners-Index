// Small helpers shared by every page. No dependencies.
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

export async function getJSON(path) {
  const r = await fetch(path, { headers: { accept: "application/json" } });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}
export async function getText(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.text();
}

export function fail(main, err) {
  main.replaceChildren(el("div", { class: "err", role: "alert" }, el("h2", { text: "The data could not be loaded" }), el("p", { text: String(err && err.message ? err.message : err) })));
}

export const store = {
  get(k, d) { try { const v = localStorage.getItem("fci:" + k); return v === null ? d : v; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("fci:" + k, v); } catch { /* private mode: the page works without it */ } },
};

const NF = {};
export function num(v, digits = 3) {
  if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
  NF[digits] ||= new Intl.NumberFormat("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return NF[digits].format(v);
}
export function pct(x, digits = 1) {
  if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
  return (x >= 0 ? "+" : "−") + num(Math.abs(x) * 100, digits) + "%";
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthLabel = (m) => `${MONTHS[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}`;
export function periodLabel(s, e) {
  const y = s.slice(0, 4);
  if (s.slice(5, 10) === "01-01" && e.slice(5, 10) === "06-30") return `${y}-S1`;
  if (s.slice(5, 10) === "07-01" && e.slice(5, 10) === "12-31") return `${y}-S2`;
  if (s.slice(5, 10) === "01-01" && e.slice(5, 10) === "12-31") return y;
  return s.slice(0, 7);
}
export function addMonths(m, k) {
  const t = Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7)) - 1 + k;
  return `${Math.floor(t / 12)}-${String((t % 12) + 1).padStart(2, "0")}`;
}
export function monthsBetween(a, b) {
  const out = [];
  for (let m = a; m <= b; m = addMonths(m, 1)) out.push(m);
  return out;
}

// Currency handling. `perEur`: units of each currency per one euro (ECB), EUR = 1.
export const CURRENCIES = ["USD", "EUR", "ZAR"];
export const DIGITS = { USD: 3, EUR: 3, ZAR: 2, GBP: 3, CNY: 3 };
export function convert(value, from, to, perEur) {
  if (from === to) return value;
  return (value / perEur[from]) * perEur[to];
}
// An index level is published in USD at each month's average rate; convert it at that month's rate.
export function levelIn(usd, cur, fxMonth) {
  if (cur === "USD") return usd;
  if (cur === "EUR") return usd / fxMonth.USD;
  return (usd * fxMonth[cur]) / fxMonth.USD;
}
export const money = (v, cur) => `${num(v, DIGITS[cur] ?? 3)} ${cur}/kWh`;
export const shortMoney = (v, cur) => num(v, DIGITS[cur] ?? 3);

export function badge(letter, low) {
  const c = el("span", { class: "chip badge", title: `Data quality ${letter}` }, `Quality ${letter}`);
  return low ? el("span", {}, c, " ", el("span", { class: "chip low", title: "Low confidence: shown with its caveat" }, "⚠ low confidence")) : c;
}
export function statusChip(status) {
  return el("span", { class: `chip ${status}`, title: status === "final" ? "All inputs are final" : "Some inputs are carried forward or preliminary" },
    status === "final" ? "✓ final" : "◐ provisional");
}
