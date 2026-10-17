"""Load the ClaimPath graph into FalkorDB. Idempotent: rebuilds the whole graph from data.py.
Batched UNWIND writes (few round trips, good for a remote hosted FalkorDB)."""
import os, sys
from falkordb import FalkorDB
sys.path.insert(0, os.path.dirname(__file__))
import data

GRAPH = os.environ.get("CLAIMPATH_GRAPH", "claimpath")


def connect():
    return FalkorDB(host=os.environ.get("FALKORDB_HOST", "localhost"),
                    port=int(os.environ.get("FALKORDB_PORT", "6379")),
                    password=os.environ.get("FALKORDB_PASSWORD") or None,
                    username=os.environ.get("FALKORDB_USERNAME") or None,
                    ssl=os.environ.get("FALKORDB_SSL") == "1")


def seed(db=None):
    db = db or connect()
    try:
        db.select_graph(GRAPH).delete()
    except Exception:
        pass
    g = db.select_graph(GRAPH)
    q = g.query
    q("UNWIND $rows AS r CREATE (:Case {id:r.id, country:r.country, flag:r.flag, currency:r.currency, title:r.title, summary:r.summary, "
      "claim_date:r.claim_date, rejection_received:r.rejection_received, insurer:r.insurer, synthetic:true})", {"rows": data.CASES})
    q("UNWIND $rows AS r MATCH (c:Case {id:r.case_id}) CREATE (c)-[:HAS_POLICY]->(:Policy {id:r.id, insurer:r.insurer, product:r.product, "
      "start_date:r.start_date, sum_insured:r.sum_insured, currency:r.currency, doc:r.doc})", {"rows": data.POLICIES})
    clauses = [dict(c, room_pct=c.get("room_pct", 0.0)) for c in data.CLAUSES]
    q("UNWIND $rows AS r MATCH (p:Policy {id:r.policy_id}) CREATE (p)-[:HAS_CLAUSE]->(:Clause {id:r.id, no:r.no, title:r.title, kind:r.kind, "
      "page:r.page, text:r.text, keywords:r.keywords, room_pct:r.room_pct})", {"rows": clauses})
    q("UNWIND $rows AS r MATCH (c:Case {id:r.case_id}), (cl:Clause {id:r.cites}) "
      "CREATE (c)-[:HAS_REJECTION]->(x:Rejection {id:r.id, case_id:r.case_id, reason:r.reason, received:r.received, amount:r.amount}) "
      "CREATE (x)-[:CITES]->(cl)", {"rows": data.REJECTIONS})
    q("UNWIND $rows AS r CREATE (:FactType {key:r.key, label:r.label, how_to_find:r.how_to_find, assume_label:r.assume_label, assume_value:r.assume_value})",
      {"rows": data.FACTS})
    ev = []
    for e in data.EVIDENCE:
        ev.append(dict(id=e["id"], case_id=e["case_id"], kind=e["kind"], label=e["label"], doc=e.get("doc", ""), date=e.get("date", ""),
                       seq=e.get("seq", 0), category=e.get("category", ""), amount=e.get("amount", 0), room_linked=e.get("room_linked", False),
                       payable=e.get("payable", True), days=e.get("days", 0), rate=e.get("rate", 0), paid=e.get("paid", 0),
                       patient=e.get("patient", 0), carc=e.get("carc", "")))
    q("UNWIND $rows AS r MATCH (c:Case {id:r.case_id}) CREATE (c)-[:HAS_EVIDENCE]->(:Evidence {id:r.id, case_id:r.case_id, kind:r.kind, label:r.label, "
      "doc:r.doc, date:r.date, seq:r.seq, category:r.category, amount:r.amount, room_linked:r.room_linked, payable:r.payable, days:r.days, "
      "rate:r.rate, paid:r.paid, patient:r.patient, carc:r.carc})", {"rows": ev})
    proves = [dict(ev=e["id"], key=k, value=v) for e in data.EVIDENCE for k, v in e.get("proves", [])]
    q("UNWIND $rows AS r MATCH (e:Evidence {id:r.ev}), (f:FactType {key:r.key}) CREATE (e)-[:PROVES {value:r.value}]->(f)", {"rows": proves})
    q("UNWIND $rows AS r CREATE (:Rule {id:r.id, jurisdiction:r.jurisdiction, name:r.name, effect:r.effect, kind:r.kind, threshold:r.threshold, "
      "terminal:r.terminal, citation:r.citation, summary:r.summary, source_url:r.source_url, source_alt:r.source_alt, verification:r.verification})",
      {"rows": data.RULES})
    q("UNWIND $rows AS r MATCH (a:Rule {id:r.a}), (b:Rule {id:r.b}) CREATE (a)-[:RELATES {kind:r.kind}]->(b)",
      {"rows": [dict(a=a, b=b, kind=k) for a, b, k in data.RULE_EDGES]})
    q("UNWIND $rows AS r MATCH (c:Clause {id:r.c}), (x:Rule {id:r.r}) CREATE (c)-[:LIMITED_BY {why:r.why}]->(x)",
      {"rows": [dict(c=c, r=r, why=w) for c, r, w in data.LIMITED_BY]})
    q("UNWIND $rows AS r MATCH (x:Rule {id:r.r}), (f:FactType {key:r.f}) CREATE (x)-[:REQUIRES {role:r.role}]->(f)",
      {"rows": [dict(r=r, f=f, role=role) for r, f, role in data.REQUIRES]})
    q("UNWIND $rows AS r MATCH (j:Rejection {id:r.j}), (x:Rule {id:r.r}) CREATE (j)-[:APPEAL_VIA]->(x)",
      {"rows": [dict(j=j, r=r) for j, r in data.APPEAL_VIA]})
    q("UNWIND $rows AS r MATCH (x:Rule {id:r.rule}) CREATE (x)-[:HAS_DEADLINE]->(:Deadline {id:r.id, ord:r.ord, label:r.label, amount:r.amount, "
      "unit:r.unit, anchor:r.anchor, kind:r.kind})", {"rows": data.DEADLINES})
    q("CREATE (:Meta {id:'rev', rev:$rev})", {"rev": data.REV})  # written last: marks a complete seed
    return g.query("MATCH (n) RETURN count(n)").result_set[0][0]


if __name__ == "__main__":
    print(f"Seeded graph '{GRAPH}': {seed()} nodes")
