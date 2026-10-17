"""Re-apply backend/classify.py to the already-selected precedents (keeps the 118-case eval set stable).
Usage: python scripts/remap_precedents.py   (rewrites backend/precedents.json using evals/cases.jsonl)"""
import json, os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(R, "backend")); import classify as C
P = json.load(open(f"{R}/backend/precedents.json")); cs = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/evals/cases.jsonl")}
ch = []
for x in P["india"] + P["us"]:
    c = cs[x["id"]]
    if x["jurisdiction"] == "IN":
        cl, oc = C.india_clause(c["body"]), C.outcome_of(c["body"])
        if oc and oc != x["outcome"]: ch.append((x["id"], "outcome", x["outcome"], oc)); x["outcome"] = oc
    else:
        cl = C.us_clause(c["treatment_category"], c["treatment_sub"], c["findings"], c["typ"])
    if (cl or "") != x["clause_id"]: ch.append((x["id"], "clause", x["clause_id"], cl)); x["clause_id"] = cl or ""
json.dump(P, open(f"{R}/backend/precedents.json", "w"), ensure_ascii=False, indent=1)
for c in ch: print(c)
print(len(ch), "changes")
