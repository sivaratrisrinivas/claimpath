const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (cur, n) => (cur === "INR" ? "Rs " + Math.round(n).toLocaleString("en-IN") : "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 }));
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
let CASES = [], sel = null, assume = [], baseMissing = [], lastCode = null, running = false, built = null;

async function init() {
  CASES = await (await fetch("/api/cases")).json();
  $("#cases").innerHTML = CASES.map((c, i) => `<button class="case" style="--tilt:${i % 2 ? 0.9 : -0.9}deg" data-id="${esc(c.id)}"><span class="tag">${c.country === "IN" ? "India" : "USA"}</span><h3>${esc(c.title)}</h3></button>`).join("");
  document.querySelectorAll(".case").forEach((b) => (b.onclick = () => { pick(b.dataset.id); run(true); }));
  $("#run").onclick = () => { if (!sel) pick(CASES[0].id); run(true); };
  $("#work-btn").onclick = () => toggleWork();
  const q = new URLSearchParams(location.search);
  if (q.get("case")) pick(q.get("case"));
  if (q.get("auto")) { if (!sel) pick(CASES[0].id); await run(true); if (q.get("work")) toggleWork(true); }
}
function toggleWork(on) {
  const w = $("#work"), open = on ?? w.classList.contains("hidden");
  w.classList.toggle("hidden", !open); $("#work-btn").setAttribute("aria-expanded", open); $("#work-btn").textContent = open ? "hide my working" : "show my working";
}
function pick(id) { sel = id; assume = []; baseMissing = []; lastCode = null; built = null; document.querySelectorAll(".case").forEach((b) => b.classList.toggle("sel", b.dataset.id === id)); }

async function run(fresh) {
  if (running) return; running = true;
  if (fresh) { assume = []; baseMissing = []; lastCode = null; }
  const res = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ case_id: sel, assume, text: $("#paste").value }) });
  if (!res.ok) { running = false; alert("The graph is unavailable: " + res.status); return; }
  const d = await res.json();
  if (fresh) baseMissing = d.missing.slice();
  $("#out").classList.remove("hidden");
  if (fresh || !built) buildLetter(d);
  renderState(d);
  renderTrace(d.trace); renderClock(d); renderBill(d); renderPrec(d); $("#letter").textContent = d.letter.text;
  lastCode = d.verdict.code; running = false;
  if (fresh) { toggleWork(false); $("#out").scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" }); }
}

/* ---- the letter ---- */
const words = (t) => t.split(/\s+/).filter(Boolean).map((w, i) => `<span class="w" style="--r:${(Math.sin(i * 12.9898) * 0.9).toFixed(2)}deg">${esc(w)}</span>`).join(" ");
function buildLetter(d) {
  built = d.case.id;
  const sheet = $("#sheet"); sheet.classList.remove("settle"); void sheet.offsetWidth; sheet.classList.add("settle");
  $("#lh-insurer").textContent = d.policy.insurer;
  $("#re").innerHTML = `${esc(d.case.rejection_received)} &middot; Re: your claim for ${money(d.case.currency, d.rejection.amount)} &middot; ${esc(d.policy.product)}`;
  $("#l1").innerHTML = words(d.reason);
  $("#l2").innerHTML = words(`Under clause ${d.clause.no} of your policy: \u201c${d.clause.text}\u201d`);
  ["#st-red", "#st-green"].forEach((s) => { const e = $(s); e.classList.remove("on"); void e.offsetWidth; });
  $("#sheet").dataset.state = "none";
}
function setStrikes(state) {
  const all = [...document.querySelectorAll("#l1 .w, #l2 .w")]; const n1 = document.querySelectorAll("#l1 .w").length;
  all.forEach((w, i) => {
    const inLine = i < n1 ? i : i - n1, len = i < n1 ? n1 : all.length - n1;
    w.classList.toggle("p", state === "pending" && inLine < len * 0.4);
    w.classList.toggle("f", state === "full");
    w.style.transitionDelay = state === "full" && !calm ? inLine * 28 + (i < n1 ? 0 : 160) + "ms" : "0ms";
  });
}
function renderState(d) {
  const v = d.verdict, s = d.strongest, sheet = $("#sheet");
  const state = v.code === "likely_contestable" ? "full" : v.code === "undecidable" && s ? "pending" : "none";
  const prev = sheet.dataset.state;
  sheet.dataset.state = state; setStrikes(state);
  const win = v.code === "likely_contestable";
  $("#st-red").classList.toggle("on", !win); $("#st-green").classList.toggle("on", win);
  if (prev === "pending" && win && !calm) { sheet.classList.remove("thud"); void sheet.offsetWidth; sheet.classList.add("thud"); }
  // margin note
  let m = "";
  if (s && state !== "none") {
    const ticks = s.facts.map((f) => f.provided ? `<li class="ok">&#10003; ${esc(f.label)}${f.assumed ? " (your document)" : ""}</li>` : `<li class="no">? ${esc(f.label)}</li>`).join("");
    m = `<div class="note ${state}"><b>${esc(s.name)}</b>${state === "pending" ? '<span class="cond">would strike this out, if the missing fact turns up</span>' : ""}<ul>${ticks}</ul><a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.citation.split(",")[0])} &#8599;</a></div>`;
  } else m = `<div class="note none"><b>No rule here beats this reason.</b></div>`;
  $("#marg").innerHTML = m;
  // verdict line
  const flipped = lastCode && lastCode !== v.code;
  $("#vline").innerHTML = `<b>${esc(v.label)}.</b> ${esc(v.headline)}${flipped ? ' <span class="chg">Verdict changed.</span>' : ""}<span class="because">${v.because.map(esc).join(" ")}</span>`;
  renderTray(d);
  $("#sheet").classList.toggle("won", win);
}

/* ---- the document gesture ---- */
function renderTray(d) {
  const wrap = $("#tray-wrap"), slips = $("#slips"), tray = $("#tray");
  if (!baseMissing.length) { wrap.classList.add("hidden"); slips.innerHTML = ""; return; }
  wrap.classList.remove("hidden");
  const on = (m) => assume.includes(m.key);
  tray.innerHTML = baseMissing.map((m) => on(m)
    ? `<div class="doc gone" aria-hidden="true"><span>On the letter</span></div>`
    : `<button class="doc" data-k="${esc(m.key)}" aria-label="Attach: ${esc(m.label)}"><span class="clip"></span><b>${esc(m.label)}</b><small>Where to look: ${esc(m.how_to_find)}</small><em>drag it onto the letter, or tap</em></button>`).join("");
  slips.innerHTML = baseMissing.filter(on).map((m, i) => `<button class="slip" data-k="${esc(m.key)}" style="--tilt:${i % 2 ? 2 : -2}deg" aria-label="Take this document off the letter"><span class="clip"></span><b>Exhibit ${String.fromCharCode(65 + i)}</b> ${esc(m.what_if_label.replace(/^Add (proof|record): /, ""))}</button>`).join("");
  tray.querySelectorAll("button.doc").forEach(dragDoc);
  slips.querySelectorAll(".slip").forEach((b) => (b.onclick = () => flip(b.dataset.k)));
}
function flip(k) { assume = assume.includes(k) ? assume.filter((x) => x !== k) : [...assume, k]; run(false); }
function dragDoc(el) {
  let sx, sy, moved = false, down = false;
  el.addEventListener("pointerdown", (e) => { down = true; moved = false; sx = e.clientX; sy = e.clientY; el.setPointerCapture(e.pointerId); el.classList.add("lift"); });
  el.addEventListener("pointermove", (e) => {
    if (!down) return; const dx = e.clientX - sx, dy = e.clientY - sy;
    if (Math.abs(dx) + Math.abs(dy) > 6) moved = true;
    el.style.transform = `translate(${dx}px,${dy}px) rotate(${Math.max(-6, Math.min(6, dx / 40))}deg)`;
    const r = $("#sheet").getBoundingClientRect(); $("#sheet").classList.toggle("target", e.clientX > r.left && e.clientX < r.right && e.clientY > r.top && e.clientY < r.bottom);
  });
  el.addEventListener("pointerup", (e) => {
    if (!down) return; down = false; el.classList.remove("lift");
    const r = $("#sheet").getBoundingClientRect(); $("#sheet").classList.remove("target");
    const over = e.clientX > r.left && e.clientX < r.right && e.clientY > r.top && e.clientY < r.bottom;
    if (!moved || over) { el.dataset.done = "1"; flip(el.dataset.k); } else el.style.transform = "";
  });
  el.addEventListener("click", (e) => { if (e.detail === 0) flip(el.dataset.k); });  // keyboard
}

/* ---- deadlines as a torn calendar strip ---- */
const MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
function renderClock(d) {
  $("#clock").innerHTML = d.clock.deadlines.map((x, i) => {
    const dt = x.due ? x.due.split("-") : null;
    const big = dt ? `<span class="mo">${MON[+dt[1] - 1]}</span><span class="dy">${+dt[2]}</span>` : `<span class="mo">within</span><span class="dy">${x.amount}</span><span class="mo">${esc(x.unit)}</span>`;
    return `<li style="--j:${i % 3}"><div class="when">${big}</div><div class="what"><span class="${x.kind === "you_must" ? "you" : "they"}">${x.kind === "you_must" ? "You must" : "They must"}</span> ${esc(x.label)}<a href="${esc(x.source_url)}" target="_blank" rel="noopener">source &#8599;</a></div></li>`;
  }).join("");
}

/* ---- working (collapsed) ---- */
function summary(t) {
  const r = t.result;
  switch (t.tool) {
    case "get_case": return `${r.policy.product}; rejection cites clause ${r.cited_clause.no} (${r.cited_clause.title})`;
    case "match_reason": return r.matched ? `matched clause ${r.clause.no} (${r.clause.title}) via: ${r.keywords_hit.join(", ")}` : r.note;
    case "rule_centrality": return "PageRank: " + r.ranking.slice(0, 3).map((x) => `${x.rule.replace("R-", "")} ${x.score}`).join(" > ");
    case "strongest_rule_path": return r.candidates.length ? r.candidates.map((c) => `${c.id}: ${c.eval.status}`).join("; ") + `  => strongest ${r.strongest}` : "no rule limits this clause";
    case "missing_facts": return r.missing.length ? r.missing.length + " missing: " + r.missing.map((m) => m.key).join(", ") : "nothing missing";
    case "reconcile_bill": return r.has_bill ? (r.country === "IN" ? `billed ${money(r.currency, r.total_billed)}; room-rent deduction ~${money(r.currency, r.proportionate_deduction)}` : `denied ${money(r.currency, r.denied_total)} on ${r.denied_lines.length} line(s)`) : "no bill";
    case "escalation_path": return r.path.map((p) => p.id.replace("R-", "").replace("REJ-", "REJ ")).join(" -> ") + ` (${r.hops} hops)`;
    case "deadline_clock": return r.deadlines.length + " deadlines from the remedy rules";
    case "precedent_lookup": return `clause ${r.clause.no}: ${r.loaded_for_clause.claimant_favoured + r.loaded_for_clause.insurer_favoured} real precedents loaded (${r.loaded_for_clause.claimant_favoured} claimant-favoured, ${r.loaded_for_clause.insurer_favoured} insurer-favoured) + ${r.related_total} via shared rule`;
    case "draft_letter": return `${r.chars} chars; ${r.placeholders.length} placeholders to fill`;
  }
  return "";
}

function renderTrace(trace) {
  const ol = $("#trace"); ol.innerHTML = ""; $("#trace-n").textContent = "(" + trace.length + " steps)";
  for (const t of trace) {
    const li = document.createElement("li"); li.className = "step";
    const cy = (t.cypher || []).map((c) => c.cypher + (Object.keys(c.params).length ? "\n// params: " + JSON.stringify(c.params) : "") + `\n// ${c.rows} rows, ${c.ms} ms`).join("\n\n");
    li.innerHTML = `<div class="t">${esc(t.tool)}</div><div class="why">${esc(t.why)}</div><div class="res">${esc(summary(t))}</div>` + (cy ? `<details><summary>Show the Cypher query</summary><pre>${esc(cy)}</pre></details>` : "");
    ol.appendChild(li);
  }
}
function renderBill(d) {
  const b = d.bill, card = $("#bill-card");
  if (!b || !b.has_bill) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const cur = b.currency, isIN = b.country === "IN";
  let h = `<table><tr><th>Line</th><th class="n">Billed</th>${isIN ? "<th>Treatment</th>" : '<th class="n">Plan paid</th><th>Status</th>'}</tr>` + b.lines.map((l) => `<tr><td>${esc(l.label)}</td><td class="n">${money(cur, l.amount)}</td>` + (isIN ? `<td>${!l.payable ? "non-payable list" : l.room_linked ? "room-linked (clause 3.2)" : "not reduced"}</td>` : `<td class="n">${money(cur, l.paid)}</td><td>${l.carc ? "<b>denied " + esc(l.carc) + "</b>" : "paid"}</td>`) + "</tr>").join("") + "</table>";
  h += `<div class="note">${esc(b.note)}</div>`;
  if (isIN) h += `<div class="note">If the rejection is overturned, expected payable is about <b>${money(cur, b.expected_payable_if_overturned)}</b> of ${money(cur, b.total_billed)} billed.</div>`;
  $("#bill").innerHTML = h;
}

function precItem(e, rel) {
  const win = e.outcome_class === "claimant";
  const amt = e.amount ? " &middot; claim " + money(e.currency, e.amount) : "";
  return `<li class="pi"><span class="oc ${win ? "w" : "l"}">${esc(win ? "Claimant succeeded" : "Insurer upheld")}</span> <b>${esc(e.forum.replace("Insurance Ombudsman", "Ombudsman"))}, ${esc(e.year)}</b>${rel ? ' <span class="rel">via ' + esc(rel) + "</span>" : ""}
    <div class="pm">${esc(e.claim_type)}${amt}${e.clause_ref ? " &middot; policy clause " + esc(e.clause_ref) : ""}</div>
    <details><summary>${esc(e.reason.length > 150 ? e.reason.slice(0, 150).replace(/\s\S*$/, "") + "..." : e.reason)}</summary><div class="ex">${esc(e.excerpt)}</div><div class="srcl">${esc(e.case_ref)} &middot; <a href="${esc(e.source_url)}" target="_blank" rel="noopener">source &#8599;</a></div></details></li>`;
}
function renderPrec(d) {
  const p = d.precedents, card = $("#prec-card");
  if (!p || !p.examples.length) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const note = d.case.country === "IN" ? "Real Ombudsman awards from 2009&ndash;2012, before today's rules. A sample, not a success rate." : "Real California independent medical reviews, 2024&ndash;2026. A sample, not a success rate.";
  $("#prec").innerHTML = `<div class="pnote">${note}</div><ul class="plist scroll">${p.examples.map((e) => precItem(e)).join("")}</ul>`;
}
$("#copy").onclick = () => { navigator.clipboard.writeText($("#letter").textContent); $("#copy").textContent = "copied"; setTimeout(() => ($("#copy").textContent = "copy"), 1500); };
$("#dl").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([$("#letter").textContent], { type: "text/plain" })); a.download = "claimpath-draft-letter.txt"; a.click(); };
init();
