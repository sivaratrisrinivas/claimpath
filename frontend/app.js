const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (cur, n) => (cur === "INR" ? "Rs " + Math.round(n).toLocaleString("en-IN") : "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 }));
let CASES = [], sel = null, assume = [], baseMissing = [], lastCode = null, running = false;

async function init() {
  CASES = await (await fetch("/api/cases")).json();
  $("#cases").innerHTML = CASES.map((c) => `<button class="case" data-id="${esc(c.id)}"><div class="tag">${c.country === "IN" ? "INDIA" : "USA"} &middot; SYNTHETIC SAMPLE</div><h3>${esc(c.title)}</h3><p>${esc(c.summary.replace("SYNTHETIC SAMPLE. ", ""))}</p></button>`).join("");
  document.querySelectorAll(".case").forEach((b) => (b.onclick = () => pick(b.dataset.id)));
  const q = new URLSearchParams(location.search);
  pick(q.get("case") || CASES[0].id);
  $("#run").onclick = () => run(true);
  $("#mcp-link").onclick = async (e) => { e.preventDefault(); const r = await (await fetch("/mcp")).json(); alert("POST JSON-RPC to /mcp\nTools: " + r.tools.join(", ")); };
  if (q.get("auto")) run(true);
}
function pick(id) { sel = id; assume = []; baseMissing = []; lastCode = null; document.querySelectorAll(".case").forEach((b) => b.classList.toggle("sel", b.dataset.id === id)); }

async function run(fresh, quick) {
  if (running) return; running = true;
  const btn = $("#run"); btn.disabled = true; btn.textContent = "Agent running...";
  if (fresh) { assume = []; baseMissing = []; lastCode = null; }
  const res = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ case_id: sel, assume, text: $("#paste").value }) });
  if (!res.ok) { btn.disabled = false; btn.textContent = "Run the agent"; running = false; alert("The graph is unavailable: " + res.status); return; }
  const d = await res.json();
  $("#out").classList.remove("hidden");
  if (fresh) { baseMissing = d.missing.slice(); }
  await renderTrace(d.trace, quick || !fresh);
  renderVerdict(d); renderPath(d); renderClock(d); renderBill(d); renderPrec(d); renderLetter(d);
  lastCode = d.verdict.code;
  btn.disabled = false; btn.textContent = "Run the agent again"; running = false;
  if (fresh) $("#out").scrollIntoView({ behavior: "smooth", block: "start" });
}

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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function renderTrace(trace, quick) {
  const ol = $("#trace"); ol.innerHTML = "";
  for (const t of trace) {
    const li = document.createElement("li"); li.className = "step";
    const cy = (t.cypher || []).map((c) => c.cypher + (Object.keys(c.params).length ? "\n// params: " + JSON.stringify(c.params) : "") + `\n// ${c.rows} rows, ${c.ms} ms`).join("\n\n");
    li.innerHTML = `<span class="ms">${t.ms} ms</span><div class="t">${esc(t.tool)}(${esc(Object.entries(t.args).filter(([k]) => k !== "text").map(([k, v]) => k + "=" + (Array.isArray(v) ? "[" + v + "]" : v)).join(", "))})</div><div class="why">${esc(t.why)}</div><div class="res">${esc(summary(t))}</div>` + (cy ? `<details><summary>Cypher (${t.cypher.length})</summary><pre>${esc(cy)}</pre></details>` : "");
    ol.appendChild(li);
    if (!quick) { li.scrollIntoView({ block: "nearest", behavior: "smooth" }); await sleep(420); }
  }
}

function renderVerdict(d) {
  const v = d.verdict, el = $("#verdict");
  el.className = "card verdict " + v.code;
  const flipped = lastCode && lastCode !== v.code;
  let h = `<span class="badge">${esc(v.label)}</span>${flipped ? '<span class="flip">verdict flipped</span>' : ""}<h3>${esc(v.headline)}</h3><div class="because">${v.because.map(esc).join("<br>")}</div>`;
  if (baseMissing.length) {
    h += `<div class="facts"><h4>Missing facts &mdash; what if you find one?</h4>` + baseMissing.map((m) => {
      const on = assume.includes(m.key);
      return `<div class="mf"><button class="sw ${on ? "on" : ""}" data-k="${esc(m.key)}" aria-label="toggle what-if"></button><div class="lbl"><div>${esc(m.label)}</div><div class="how">${on ? '<span class="swlbl">What-if on</span> ' + esc(m.what_if_label) : "Where to look: " + esc(m.how_to_find)}</div></div></div>`;
    }).join("") + `</div>`;
  }
  el.innerHTML = h;
  el.querySelectorAll(".sw").forEach((b) => (b.onclick = () => { const k = b.dataset.k; assume = assume.includes(k) ? assume.filter((x) => x !== k) : [...assume, k]; run(false, true); }));
}

function renderPath(d) {
  const s = d.strongest, ol = $("#path");
  const nodes = [];
  nodes.push(["Insurer's reason", `<blockquote>${esc(d.reason)}</blockquote>`]);
  nodes.push(["Policy clause", `<div><b>${esc(d.clause.no)} ${esc(d.clause.title)}</b> <small>(${esc(d.policy.product)}, ${esc(d.clause.page)})</small></div><blockquote>${esc(d.clause.text)}</blockquote>`]);
  if (s) {
    nodes.push(["Your evidence", s.facts.length ? s.facts.map((f) => f.provided ? `<div class="ev ${f.assumed ? "what" : "ok"}"><b>${f.assumed ? "What-if: " : "&#10003; "}${esc(f.label)}</b>${f.value ? ": " + esc(f.value) : ""}<span class="src">${f.evidence.map((e) => esc(e.label) + " &middot; " + esc(e.doc)).join("<br>")}</span></div>` : `<div class="ev miss"><b>&#9888; Not found: ${esc(f.label)}</b><span class="src">${esc(f.how_to_find)}</span></div>`).join("") : "<div>This clause is not limited by any rule that depends on your evidence.</div>"]);
    nodes.push(["Governing rule", `<div><b>${esc(s.name)}</b></div><div>${esc(s.summary)}</div><div class="src"><a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.citation)} &#8599;</a>${s.source_alt ? ` &middot; <a href="${esc(s.source_alt)}" target="_blank" rel="noopener">second source</a>` : ""}</div><div class="ver">How verified: ${esc(s.verification)}</div>${d.candidates.length > 1 ? `<details><summary>${d.candidates.length - 1} other rule(s) also apply</summary>${d.candidates.filter((c) => c.id !== s.id).map((c) => `<div class="ev"><b>${esc(c.name)}</b><span class="src"><a href="${esc(c.source_url)}" target="_blank" rel="noopener">${esc(c.citation)} &#8599;</a></span></div>`).join("")}</details>` : ""}`]);
  } else nodes.push(["Governing rule", "<div>No rule in the graph limits this clause.</div>"]);
  nodes.push(["Verdict", `<div><b>${esc(d.verdict.label)}</b>: ${esc(d.verdict.headline)}</div>`]);
  ol.innerHTML = nodes.map((n, i) => `<li class="pn"><div class="dot">${i + 1}</div><div><div class="k">${esc(n[0])}</div><div class="v">${n[1]}</div></div></li>`).join("");
}

function renderClock(d) {
  $("#clock-sub").textContent = "as of " + d.clock.as_of + " - dates from your filing are projected as if you file today";
  $("#clock").innerHTML = d.clock.deadlines.map((x) => `<li><div class="d">${x.due ? esc(x.due) : "relative"}</div><div><div class="lab"><span class="${x.kind === "you_must" ? "you" : "they"}">${x.kind === "you_must" ? "YOU MUST" : "THEY MUST"}</span> ${esc(x.label)}</div><div class="meta">${x.days_left !== null ? x.days_left + " days from today &middot; " : ""}${esc(x.basis)} &middot; <a href="${esc(x.source_url)}" target="_blank" rel="noopener">source</a></div></div></li>`).join("");
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
  return `<li class="pi"><span class="oc ${win ? "w" : "l"}">${esc(win ? "Claimant succeeded" : "Insurer upheld")}</span> <b>${esc(e.forum.replace("Insurance Ombudsman", "Ombudsman"))}, ${esc(e.year)}</b>${e.pre_current_rules ? ' <span class="old">pre-2017 rules</span>' : ""}${rel ? ' <span class="rel">via ' + esc(rel) + "</span>" : ""}
    <div class="pm">${esc(e.claim_type)}${amt}${e.clause_ref ? " &middot; policy clause " + esc(e.clause_ref) : ""}</div>
    <details><summary>${esc(e.reason.length > 150 ? e.reason.slice(0, 150).replace(/\s\S*$/, "") + "..." : e.reason)}</summary><div class="ex">${esc(e.excerpt)}</div><div class="srcl">${esc(e.case_ref)} &middot; <a href="${esc(e.source_url)}" target="_blank" rel="noopener">source &#8599;</a></div></details></li>`;
}
function renderPrec(d) {
  const p = d.precedents, card = $("#prec-card");
  if (!p || (!p.examples.length && !p.related.length)) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const n = p.loaded_for_clause, india = d.case.country === "IN";
  let h = `<div class="pnote">Real decisions on a clause like <b>${esc(p.clause.no)} ${esc(p.clause.title)}</b>: ${n.claimant_favoured + n.insurer_favoured} loaded (${n.claimant_favoured} claimant-favoured, ${n.insurer_favoured} insurer-favoured). Illustrative sample, <b>not a success rate</b>.</div>`;
  if (india) h += `<div class="pwarn">India awards here are from <b>2009&ndash;2012</b> and pre-date the Ombudsman Rules 2017 and today's IRDAI rules. They show how such disputes were argued, not how they would be decided now.</div>`;
  else h += `<div class="pwarn">California state-regulated plans (DMHC Independent Medical Review, 2024&ndash;2026); outcome is on medical-necessity review, which is a different question from a prior-authorization technicality.</div>`;
  h += `<ul class="plist scroll">${p.examples.map((e) => precItem(e)).join("")}</ul>`;
  if (p.related.length) h += `<details class="relwrap"><summary>Also under the same governing rule (${p.related_total} more loaded; ${p.related.length} shown)</summary><ul class="plist">${p.related.map((e) => precItem(e, e.related_clause)).join("")}</ul></details>`;
  h += `<div class="pnote small">Sources: ${india ? '<a href="https://www.cioins.co.in/" target="_blank" rel="noopener">Council for Insurance Ombudsmen</a>' : '<a href="https://data.chhs.ca.gov/dataset/independent-medical-review-imr-determinations-trend" target="_blank" rel="noopener">California DMHC IMR data (CHHS)</a>'} &middot; <a href="#" id="attr-open">licences &amp; caveats</a></div>`;
  $("#prec").innerHTML = h;
  $("#attr-open").onclick = (e) => { e.preventDefault(); const dt = document.querySelector("footer.attr details"); dt.open = true; dt.scrollIntoView({ behavior: "smooth" }); };
}

function renderLetter(d) { $("#letter").textContent = d.letter.text; }
$("#copy").onclick = () => { navigator.clipboard.writeText($("#letter").textContent); $("#copy").textContent = "Copied"; setTimeout(() => ($("#copy").textContent = "Copy text"), 1500); };
$("#dl").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([$("#letter").textContent], { type: "text/plain" })); a.download = "claimpath-draft-letter.txt"; a.click(); };
init();
