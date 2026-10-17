"""Agent tools. Each tool runs Cypher against FalkorDB and returns data plus the exact Cypher it ran, so the UI trace panel,
the agent and the /mcp endpoint all use the same code. No tool writes to the graph (what-ifs are query parameters)."""
import re, time, datetime as dt
import data

TODAY = lambda: dt.date.today().isoformat()


def months_between(a, b):
    """Complete calendar months from date a to date b (ISO strings)."""
    a, b = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    m = (b.year - a.year) * 12 + (b.month - a.month)
    return m - (1 if b.day < a.day else 0)


def add_months(d, n):
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    m += 1
    import calendar
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


class Ctx:
    """Records every Cypher statement a tool runs."""
    def __init__(self, runner):
        self.runner, self.log = runner, []

    def q(self, cypher, params=None):
        t = time.time()
        rows = self.runner(cypher, params or {})
        self.log.append({"cypher": " ".join(cypher.split()), "params": params or {}, "rows": len(rows), "ms": round((time.time() - t) * 1000)})
        return rows


# ---------------------------------------------------------------- tools
def get_case(ctx, case_id):
    rows = ctx.q("""MATCH (c:Case {id:$cid})-[:HAS_POLICY]->(p:Policy)
MATCH (c)-[:HAS_REJECTION]->(j:Rejection)-[:CITES]->(cl:Clause)
RETURN c.id, c.country, c.title, c.summary, c.currency, c.rejection_received, c.claim_date, p.id, p.insurer, p.product, p.start_date, p.sum_insured,
       j.id, j.reason, j.amount, cl.id, cl.no, cl.title, cl.text, cl.page""", {"cid": case_id})
    if not rows:
        raise KeyError(f"unknown case {case_id}")
    r = rows[0]
    return {"case": {"id": r[0], "country": r[1], "title": r[2], "summary": r[3], "currency": r[4], "rejection_received": r[5], "claim_date": r[6]},
            "policy": {"id": r[7], "insurer": r[8], "product": r[9], "start_date": r[10], "sum_insured": r[11]},
            "rejection": {"id": r[12], "reason": r[13], "amount": r[14]},
            "cited_clause": {"id": r[15], "no": r[16], "title": r[17], "text": r[18], "page": r[19]}}


def match_reason(ctx, case_id, text):
    rows = ctx.q("""MATCH (:Case {id:$cid})-[:HAS_POLICY]->(:Policy)-[:HAS_CLAUSE]->(cl:Clause)
RETURN cl.id, cl.no, cl.title, cl.text, cl.page, cl.keywords""", {"cid": case_id})
    low = text.lower()
    scored = []
    for cid, no, title, ctext, page, kws in rows:
        hits = [k for k in kws if k in low]
        scored.append((len(hits), cid, no, title, ctext, page, hits))
    scored.sort(key=lambda s: -s[0])
    best = scored[0]
    if best[0] == 0:
        return {"matched": False, "note": "No clause keywords found in the pasted text; keeping the sample rejection's clause."}
    return {"matched": True, "clause": {"id": best[1], "no": best[2], "title": best[3], "text": best[4], "page": best[5]}, "keywords_hit": best[6],
            "candidates": [{"id": s[1], "no": s[2], "score": s[0]} for s in scored if s[0]]}


def rule_centrality(ctx, jurisdiction):
    cy = "CALL algo.pageRank('Rule', 'RELATES') YIELD node, score WHERE node.jurisdiction = $j RETURN node.id, node.name, score ORDER BY score DESC"
    rows = ctx.q(cy, {"j": jurisdiction})
    return {"algorithm": "PageRank over (:Rule)-[:RELATES]->(:Rule)", "ranking": [{"rule": r[0], "name": r[1], "score": round(r[2], 4)} for r in rows]}


def _rule_eval(rule, facts, claim_date):
    """Deterministic date math in code; the graph supplies the facts. facts: key -> {provided, value, assumed}."""
    core_missing = [k for k, f in facts.items() if f["role"] == "core" and not f["provided"]]
    ext_missing = [k for k, f in facts.items() if f["role"] == "extends" and not f["provided"]]
    if rule["kind"] == "months_threshold":
        starts = [f["value"] for k, f in facts.items() if k.endswith("cover_start") and f["provided"] and f["value"]]
        if core_missing or not starts or not claim_date:
            return {"status": "pending", "missing": core_missing, "why": "Core dates are missing."}
        earliest = min(starts)
        months = months_between(earliest, claim_date)
        ok = months >= rule["threshold"]
        why = (f"Continuous cover since {earliest} = {months} complete months at {claim_date}; the rule needs {rule['threshold']}.")
        if ok:
            return {"status": "satisfied", "missing": [], "months": months, "why": why}
        if ext_missing:
            return {"status": "pending", "missing": ext_missing, "months": months,
                    "why": why + " Earlier continuous cover (if you have it) would change this."}
        return {"status": "not_satisfied", "missing": [], "months": months, "why": why}
    if rule["kind"] == "all_facts":
        if core_missing:
            return {"status": "pending", "missing": core_missing, "why": "A fact the rule depends on is not in your evidence yet."}
        return {"status": "satisfied", "missing": [], "why": "All facts the rule depends on are present."}
    return {"status": "n/a", "missing": [], "why": ""}


def strongest_rule_path(ctx, case_id, clause_id, assume=(), ranking=None):
    """Rejection -> Clause -> Rule -> FactType <- Evidence, in one multi-hop query. Returns candidate rules with an evaluation."""
    cy = """MATCH (cl:Clause {id:$clid})
OPTIONAL MATCH (cl)-[lb:LIMITED_BY]->(r:Rule)
OPTIONAL MATCH (r)-[rq:REQUIRES]->(ft:FactType)
OPTIONAL MATCH (ev:Evidence {case_id:$cid})-[pv:PROVES]->(ft)
RETURN r.id, r.name, r.citation, r.summary, r.source_url, r.source_alt, r.verification, r.kind, r.threshold, r.effect, lb.why,
       ft.key, ft.label, rq.role, ft.assume_value, ft.assume_label, ft.how_to_find, ev.id, ev.label, ev.doc, pv.value"""
    rows = ctx.q(cy, {"clid": clause_id, "cid": case_id})
    case = ctx.q("MATCH (c:Case {id:$cid}) RETURN c.claim_date", {"cid": case_id})[0][0]
    rules = {}
    for (rid, name, cit, summ, src, alt, ver, kind, thr, eff, why, fk, flabel, role, aval, alabel, how, evid, evlabel, evdoc, pval) in rows:
        if rid is None:
            continue
        r = rules.setdefault(rid, dict(id=rid, name=name, citation=cit, summary=summ, source_url=src, source_alt=alt, verification=ver, kind=kind,
                                       threshold=thr, effect=eff, why=why, facts={}))
        if fk is None:
            continue
        f = r["facts"].setdefault(fk, dict(key=fk, label=flabel, role=role, provided=False, assumed=False, value=None, evidence=[], assume_label=alabel,
                                           how_to_find=how, _assume_value=aval))
        if evid is not None:
            f["provided"] = True
            f["value"] = pval if f["value"] is None or (pval and pval < f["value"]) else f["value"]
            f["evidence"].append({"id": evid, "label": evlabel, "doc": evdoc})
    for r in rules.values():
        for f in r["facts"].values():
            if not f["provided"] and f["key"] in assume:
                f.update(provided=True, assumed=True, value=f["_assume_value"] or None,
                         evidence=[{"id": "WHAT-IF", "label": f["assume_label"], "doc": "assumed (what-if)"}])
        claim = r["facts"].get("claim_date", {}).get("value") or case
        r["eval"] = _rule_eval(r, r["facts"], claim)
        r["facts"] = list(r["facts"].values())
        for f in r["facts"]:
            f.pop("_assume_value", None)
    rank = {x["rule"]: x["score"] for x in (ranking or [])}
    order = {"satisfied": 0, "pending": 1, "not_satisfied": 2, "n/a": 3}
    cands = sorted(rules.values(), key=lambda r: (r["effect"] != "bars", order.get(r["eval"]["status"], 9), -rank.get(r["id"], 0)))
    for r in cands:
        r["pagerank"] = rank.get(r["id"])
    return {"clause_id": clause_id, "candidates": cands, "strongest": cands[0]["id"] if cands else None}


def missing_facts(ctx, case_id, clause_id, assume=()):
    cy = """MATCH (:Clause {id:$clid})-[:LIMITED_BY]->(r:Rule)-[rq:REQUIRES]->(ft:FactType)
OPTIONAL MATCH (ev:Evidence {case_id:$cid})-[:PROVES]->(ft)
WITH r, rq, ft, ev WHERE ev IS NULL AND NOT ft.key IN $assume AND r.effect = 'bars'
RETURN DISTINCT ft.key, ft.label, ft.how_to_find, ft.assume_label, rq.role, collect(r.id)"""
    rows = ctx.q(cy, {"clid": clause_id, "cid": case_id, "assume": list(assume)})
    return {"missing": [{"key": r[0], "label": r[1], "how_to_find": r[2], "what_if_label": r[3], "role": r[4], "needed_by": r[5]} for r in rows]}


def reconcile_bill(ctx, case_id, assume=()):
    cy = """MATCH (c:Case {id:$cid})-[:HAS_EVIDENCE]->(b:Evidence {kind:'bill_line'})
RETURN b.seq, b.label, b.category, b.amount, b.room_linked, b.payable, b.days, b.rate, b.paid, b.patient, b.carc ORDER BY b.seq"""
    rows = ctx.q(cy, {"cid": case_id})
    if not rows:
        return {"has_bill": False}
    lines = [dict(seq=r[0], label=r[1], category=r[2], amount=r[3], room_linked=r[4], payable=r[5], days=r[6], rate=r[7], paid=r[8], patient=r[9], carc=r[10]) for r in rows]
    agg = ctx.q("""MATCH (:Case {id:$cid})-[:HAS_EVIDENCE]->(b:Evidence {kind:'bill_line'})
RETURN sum(b.amount), sum(CASE WHEN b.payable THEN b.amount ELSE 0 END), sum(CASE WHEN b.room_linked THEN b.amount ELSE 0 END), sum(b.paid), sum(b.patient)""", {"cid": case_id})[0]
    total, payable, room_linked, paid, patient = agg
    pol = ctx.q("""MATCH (:Case {id:$cid})-[:HAS_POLICY]->(p:Policy)-[:HAS_CLAUSE]->(cl:Clause {id:$lim})
RETURN p.sum_insured, p.currency, cl.room_pct, cl.no, cl.text""", {"cid": case_id, "lim": "IN-3.1"})
    if pol:  # India: room-rent proportionate deduction (policy clause 3.1 / 3.2)
        si, cur, pct, cno, ctext = pol[0]
        room = next((l for l in lines if l["category"] == "Room rent"), None)
        eligible = si * pct
        ratio = min(1.0, eligible / room["rate"]) if room and room["rate"] else 1.0
        ded = round(room_linked * (1 - ratio))
        expected = min(si, payable - ded)
        return {"has_bill": True, "country": "IN", "currency": cur, "lines": lines, "total_billed": total, "non_payable": total - payable,
                "room_rent": {"rate_charged": room["rate"], "eligible_per_day": eligible, "ratio": round(ratio, 4), "clause": f"3.1 / 3.2"},
                "room_linked_total": room_linked, "proportionate_deduction": ded, "expected_payable_if_overturned": expected,
                "note": (f"If the rejection is overturned, the insurer may still apply clause 3.2: room charged Rs {room['rate']:,}/day vs eligible Rs {eligible:,.0f}/day "
                         f"(ratio {ratio:.2%}) reduces ONLY the room-linked lines (Rs {room_linked:,}) by about Rs {ded:,}. Check that medicines, diagnostics and implants are not reduced.")}
    denied = [l for l in lines if l["carc"]]
    return {"has_bill": True, "country": "US", "currency": "USD", "lines": lines, "total_billed": total, "plan_paid": paid, "patient_owes": patient,
            "denied_lines": denied, "denied_total": sum(l["amount"] for l in denied),
            "note": f"{len(denied)} line(s) denied with remark code CO-197 (authorization absent) totalling ${sum(l['amount'] for l in denied):,.2f}; the plan paid the other lines on the same date."}


def escalation_path(ctx, rejection_id, jurisdiction):
    cy = """MATCH (j:Rejection {id:$rid}), (t:Rule {terminal:true, jurisdiction:$j})
WITH shortestPath((j)-[:APPEAL_VIA|RELATES*..6]->(t)) AS p
RETURN [n IN nodes(p) | coalesce(n.name, n.id)], [n IN nodes(p) | n.id], [n IN nodes(p) | n.source_url], length(p)"""
    rows = ctx.q(cy, {"rid": rejection_id, "j": jurisdiction})
    if not rows:
        return {"path": []}
    names, ids, urls, n = rows[0]
    return {"algorithm": "shortestPath over APPEAL_VIA|RELATES", "hops": n,
            "path": [{"id": i, "name": nm, "source_url": u} for i, nm, u in zip(ids, names, urls)]}


def deadline_clock(ctx, rejection_id, as_of=None, filing_date=None):
    as_of = as_of or TODAY()
    filing_date = filing_date or as_of
    cy = """MATCH (j:Rejection {id:$rid})-[:APPEAL_VIA]->(r0:Rule)-[:RELATES*0..3]->(r:Rule)-[:HAS_DEADLINE]->(d:Deadline)
RETURN DISTINCT d.id, d.ord, d.label, d.amount, d.unit, d.anchor, d.kind, r.id, r.name, r.source_url, j.received ORDER BY d.ord"""
    rows = ctx.q(cy, {"rid": rejection_id})
    today = dt.date.fromisoformat(as_of)
    out = []
    for did, ordn, label, amt, unit, anchor, kind, rid, rname, src, received in rows:
        base = {"rejection_received": received, "filing": filing_date}.get(anchor)
        due = None
        if base:
            b = dt.date.fromisoformat(base)
            due = (b + dt.timedelta(days=amt)) if unit == "days" else add_months(b, amt)
        out.append({"id": did, "order": ordn, "label": label, "kind": kind, "anchor": anchor, "amount": amt, "unit": unit,
                    "due": due.isoformat() if due else None, "days_left": (due - today).days if due else None,
                    "basis": (f"{amt} {unit} after " + {"rejection_received": f"you received the rejection ({received})", "filing": f"you file ({filing_date}; projected)",
                                                        "final_determination": "you receive the final internal denial", "external_request": "the reviewer receives your request"}[anchor]),
                    "rule_id": rid, "rule": rname, "source_url": src})
    return {"as_of": as_of, "deadlines": out}


def draft_letter(ctx, case_id, result):
    """Pure templating from the other tools' outputs (no model). Marks assumed facts so nothing unverified is asserted."""
    from letter import build
    return build(result)


def rule_catalog(ctx, jurisdiction=None):
    rows = ctx.q("""MATCH (r:Rule) WHERE $j IS NULL OR r.jurisdiction = $j
RETURN r.id, r.name, r.citation, r.source_url, r.effect, r.verification ORDER BY r.id""", {"j": jurisdiction})
    return {"rules": [dict(id=r[0], name=r[1], citation=r[2], source_url=r[3], effect=r[4], verification=r[5]) for r in rows]}


S = lambda **p: {"type": "object", "properties": p, "additionalProperties": False}
STR = {"type": "string"}
TOOLS = {
    "get_case": dict(fn=get_case, desc="Load a sample claim case: policy, the insurer's rejection reason and the policy clause it cites.",
                     schema={**S(case_id={"type": "string", "enum": ["IN-01", "US-01"]}), "required": ["case_id"]}),
    "match_reason": dict(fn=match_reason, desc="Match pasted rejection text to the policy clause it most likely relies on (keyword overlap against clause nodes).",
                         schema={**S(case_id=STR, text=STR), "required": ["case_id", "text"]}),
    "rule_centrality": dict(fn=rule_centrality, desc="Run PageRank inside FalkorDB over the rule graph to rank how central each rule is (used to break ties).",
                            schema={**S(jurisdiction={"type": "string", "enum": ["IN", "US"]}), "required": ["jurisdiction"]}),
    "strongest_rule_path": dict(fn=strongest_rule_path, desc="Traverse Clause -> Rule -> required facts <- your evidence and evaluate each rule that limits the clause. Returns the strongest rule with sources.",
                                schema={**S(case_id=STR, clause_id=STR, assume={"type": "array", "items": STR}), "required": ["case_id", "clause_id"]}),
    "missing_facts": dict(fn=missing_facts, desc="List facts the governing rules need that your evidence does not yet prove, with how to find each.",
                          schema={**S(case_id=STR, clause_id=STR, assume={"type": "array", "items": STR}), "required": ["case_id", "clause_id"]}),
    "reconcile_bill": dict(fn=reconcile_bill, desc="Reconcile the hospital bill / EOB against the policy: room-rent proportionate deduction (India) or denied lines (US).",
                           schema={**S(case_id=STR), "required": ["case_id"]}),
    "escalation_path": dict(fn=escalation_path, desc="shortestPath from the rejection to the final free forum (Ombudsman / external review) through the rule graph.",
                            schema={**S(rejection_id=STR, jurisdiction={"type": "string", "enum": ["IN", "US"]}), "required": ["rejection_id", "jurisdiction"]}),
    "deadline_clock": dict(fn=deadline_clock, desc="Deadlines triggered by the remedy rules, as dates from the rejection date and projected from a filing date.",
                           schema={**S(rejection_id=STR, as_of=STR, filing_date=STR), "required": ["rejection_id"]}),
    "rule_catalog": dict(fn=rule_catalog, desc="List the rules in the graph with citation, source URL and verification note.",
                         schema=S(jurisdiction={"type": "string", "enum": ["IN", "US"]})),
}


def call_tool(name, args, runner, ranking=None):
    t = time.time()
    ctx = Ctx(runner)
    kw = dict(args)
    if ranking is not None and name == "strongest_rule_path":
        kw["ranking"] = ranking  # PageRank scores from the previous tool call, used only to break ties
    result = TOOLS[name]["fn"](ctx, **kw)
    return {"tool": name, "args": args, "cypher": ctx.log, "result": result, "ms": round((time.time() - t) * 1000)}
