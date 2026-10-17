"""Rule-based agent (no LLM key needed). It plans tool calls from what the case contains and logs every call.
The verdict is a pure function of the graph query results."""
import tools as T


def _verdict(country, cands, missing, assumed):
    bars = [c for c in cands if c["effect"] == "bars"]
    proc = [c for c in cands if c["effect"] == "procedural"]
    sat = [c for c in bars if c["eval"]["status"] == "satisfied"]
    pend = [c for c in bars if c["eval"]["status"] == "pending"]
    if sat:
        c = sat[0]
        return dict(code="likely_contestable", label="Likely contestable", rule_id=c["id"],
                    headline=f"The insurer's reason runs into a rule: {c['name']}.", because=[c["eval"]["why"]] + ([f"Relies on a what-if assumption: {', '.join(assumed)}."] if assumed else []), missing=[])
    if pend:
        c = pend[0]
        names = [m["label"] for m in missing]
        return dict(code="undecidable", label="Undecidable until a fact is found", rule_id=c["id"],
                    headline=f"A rule could defeat this rejection, but your evidence can't show it yet: {c['name']}.",
                    because=[c["eval"]["why"]], missing=missing)
    if bars:
        c = bars[0]
        return dict(code="likely_valid", label="Likely valid", rule_id=c["id"], headline="Your evidence does not bring you inside the protective rule, so the rejection looks valid on this clause.",
                    because=[c["eval"]["why"]], missing=[])
    why = ["No substantive rule in this graph limits the cited clause."]
    if proc:
        why.append("Procedural rights still apply: " + "; ".join(c["name"] for c in proc) + ".")
    return dict(code="likely_valid", label="Likely valid", rule_id=None, headline="No rule in this graph limits the clause the insurer relied on.", because=why, missing=[])


def analyze(case_id, assume, text, today, runner):
    trace, assume = [], list(assume or [])

    def step(name, why, args, _ranking=None):
        out = T.call_tool(name, args, runner, ranking=_ranking)
        out["why"] = why
        trace.append(out)
        return out["result"]

    cs = step("get_case", "Load the policy, the rejection and the clause it cites.", {"case_id": case_id})
    country = cs["case"]["country"]
    clause = cs["cited_clause"]
    reason = cs["rejection"]["reason"]
    if text and text.strip():
        m = step("match_reason", "You pasted rejection text: find the policy clause it relies on.", {"case_id": case_id, "text": text.strip()})
        reason = text.strip()
        if m["matched"]:
            clause = m["clause"]
    rank = step("rule_centrality", "Rank the jurisdiction's rules by PageRank so ties break toward the most connected rule.", {"jurisdiction": country})
    res = step("strongest_rule_path", f"Walk clause {clause['no']} -> governing rules -> required facts <- your evidence.",
               {"case_id": case_id, "clause_id": clause["id"], "assume": assume}, _ranking=rank["ranking"])
    cands = res["candidates"]
    mf = step("missing_facts", "Which facts would the governing rules need that the evidence doesn't prove?", {"case_id": case_id, "clause_id": clause["id"], "assume": assume})
    bill = step("reconcile_bill", "Reconcile the hospital bill / EOB against the policy.", {"case_id": case_id})
    esc = step("escalation_path", "Find the shortest route from this rejection to the final free forum.", {"rejection_id": cs["rejection"]["id"], "jurisdiction": country})
    clock = step("deadline_clock", "Compute the deadlines the remedy rules start.", {"rejection_id": cs["rejection"]["id"], "as_of": today})
    assumed = [f["label"] for c in cands for f in c["facts"] if f["assumed"]]
    assumed = sorted(set(assumed))
    verdict = _verdict(country, cands, mf["missing"], assumed)
    strongest = next((c for c in cands if c["id"] == verdict["rule_id"]), cands[0] if cands else None)
    result = dict(case=cs["case"], policy=cs["policy"], reason=reason, clause=clause, rejection=cs["rejection"], strongest=strongest, candidates=cands,
                  missing=mf["missing"], bill=bill, escalation=esc, clock=clock, verdict=verdict, assume=assume, assumed_labels=assumed, today=today)
    from letter import build
    letter = build(result)
    trace.append({"tool": "draft_letter", "args": {"case_id": case_id, "assume": assume}, "cypher": [], "ms": 0,
                  "why": "Template the appeal text from the path, verdict and deadlines (no model; nothing is filed or sent).",
                  "result": {"chars": len(letter["text"]), "placeholders": letter["placeholders"]}})
    result["letter"] = letter
    result["trace"] = trace
    return result
