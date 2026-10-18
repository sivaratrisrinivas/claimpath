# Cypher queries and graph algorithms (all 10 tools)

Back to the [README](../README.md). The README shows the four key queries; this page has the schema, the agent tools and all ten.

## How the graph is the product (detail)

If you take FalkorDB out, there is nothing left: every tool is a Cypher query, and the verdict is computed from the traversal results. The hosted/local database is the only store.

```
(Case)-[:HAS_POLICY]->(Policy)-[:HAS_CLAUSE]->(Clause)
(Case)-[:HAS_REJECTION]->(Rejection)-[:CITES]->(Clause)
(Clause)-[:LIMITED_BY {why}]->(Rule {source_url, citation, verification, effect, kind, threshold})
(Rule)-[:REQUIRES {role: core|extends}]->(FactType {key, label, how_to_find})
(Evidence {case_id, kind, date, amount})-[:PROVES {value}]->(FactType)
(Case)-[:HAS_EVIDENCE]->(Evidence)         // documents, adverse evidence, hospital bill lines
(Rejection)-[:APPEAL_VIA]->(Rule)          // first remedy
(Rule)-[:RELATES {kind: supports|escalates}]->(Rule)
(Rule)-[:HAS_DEADLINE]->(Deadline {amount, unit, anchor, kind})
(Precedent {outcome, year, forum, source_url, ...})-[:ANALOGOUS_TO]->(Clause)   // REAL past decisions, context only
(Precedent)-[:BEARS_ON]->(Rule)                                              // via the clause's LIMITED_BY rule
```

**Multi-hop traversal** (`strongest_rule_path`): Clause -> Rule -> FactType <- Evidence in one query; the rule is evaluated in code from those facts (date math is code, not a model).

```cypher
MATCH (cl:Clause {id:$clid})
OPTIONAL MATCH (cl)-[lb:LIMITED_BY]->(r:Rule)
OPTIONAL MATCH (r)-[rq:REQUIRES]->(ft:FactType)
OPTIONAL MATCH (ev:Evidence {case_id:$cid})-[pv:PROVES]->(ft)
RETURN r.id, r.name, r.citation, ..., ft.key, rq.role, ev.id, pv.value
```

**Graph algorithms as tools:** `rule_centrality` runs `CALL algo.pageRank('Rule','RELATES')` inside FalkorDB to break ties between rules; `escalation_path` uses `shortestPath((rejection)-[:APPEAL_VIA|RELATES*..6]->(terminal:Rule))` to find the route to the final free forum (Ombudsman / external review).

**What-if is a query parameter, not a write:** `assume=["prior_cover_start"]` marks a missing FactType as provided for one request. Nothing is persisted, so visitors never affect each other.

### Agent tools (the in-page trace and `/mcp` use the same registry)

| Tool | What it does | Graph feature |
|---|---|---|
| `get_case` | Policy, rejection reason, cited clause | pattern match |
| `match_reason` | Pasted rejection text -> best clause | clause keyword nodes |
| `rule_centrality` | Ranks the jurisdiction's rules | **PageRank** |
| `strongest_rule_path` | Clause -> Rule -> required facts <- evidence, evaluated | **multi-hop traversal** |
| `missing_facts` | Facts the rules need that evidence doesn't prove | OPTIONAL MATCH anti-join |
| `reconcile_bill` | Bill vs policy: room-rent proportionate deduction (IN) / denied lines (US) | aggregation |
| `escalation_path` | Rejection -> final free forum | **shortestPath** |
| `deadline_clock` | Deadlines the remedy rules start | variable-length traversal |
| `precedent_lookup` | REAL past decisions analogous to the cited clause, plus ones on other clauses under the same rule (context only, never changes the verdict) | **2-hop traversal** Clause -> Rule <- Clause <- Precedent |
| `rule_catalog` | Rules with source URL + verification note | scan |

The agent is rule-based (no LLM key). It plans tool calls from the case, logs **every** call with its Cypher, parameters, row count and timing, and shows them under "show my working". The `/mcp` endpoint (JSON-RPC over HTTP: `initialize`, `tools/list`, `tools/call`) lets any MCP client pick the same tools:

```bash
curl -s -X POST https://claimpath-srini5.vercel.app/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"missing_facts","arguments":{"case_id":"IN-01","clause_id":"IN-7.2"}}}'
```

## One sample Cypher per tool

Sample Cypher per tool (trimmed from `backend/tools.py`; every call's real query, params, row count and latency is shown in the app under "show my working"):

| Tool | Sample Cypher |
|---|---|
| `get_case` | `MATCH (c:Case {id:$cid})-[:HAS_POLICY]->(p:Policy) MATCH (c)-[:HAS_REJECTION]->(j:Rejection)-[:CITES]->(cl:Clause) RETURN c.id, p.insurer, j.reason, cl.no, cl.text` |
| `match_reason` | `MATCH (:Case {id:$cid})-[:HAS_POLICY]->(:Policy)-[:HAS_CLAUSE]->(cl:Clause) RETURN cl.id, cl.no, cl.text, cl.keywords` (keywords scored against the pasted text) |
| `rule_centrality` | `CALL algo.pageRank('Rule','RELATES') YIELD node, score WHERE node.jurisdiction = $j RETURN node.id, node.name, score ORDER BY score DESC` |
| `strongest_rule_path` | `MATCH (cl:Clause {id:$clid}) OPTIONAL MATCH (cl)-[lb:LIMITED_BY]->(r:Rule) OPTIONAL MATCH (r)-[rq:REQUIRES]->(ft:FactType) OPTIONAL MATCH (ev:Evidence {case_id:$cid})-[pv:PROVES]->(ft) RETURN r.id, r.effect, ft.key, ev.id` |
| `missing_facts` | `MATCH (:Clause {id:$clid})-[:LIMITED_BY]->(r:Rule)-[rq:REQUIRES]->(ft:FactType) OPTIONAL MATCH (ev:Evidence {case_id:$cid})-[:PROVES]->(ft) WITH r, rq, ft, ev WHERE ev IS NULL AND r.effect = 'bars' RETURN DISTINCT ft.key, ft.how_to_find` |
| `reconcile_bill` | `MATCH (c:Case {id:$cid})-[:HAS_EVIDENCE]->(b:Evidence {kind:'bill_line'}) RETURN b.label, b.amount, b.payable, b.paid ORDER BY b.seq` |
| `escalation_path` | `MATCH (j:Rejection {id:$rid}), (t:Rule {terminal:true, jurisdiction:$j}) WITH shortestPath((j)-[:APPEAL_VIA\|RELATES*..6]->(t)) AS p RETURN [n IN nodes(p) \| n.id], length(p)` |
| `deadline_clock` | `MATCH (j:Rejection {id:$rid})-[:APPEAL_VIA]->(r0:Rule)-[:RELATES*0..3]->(r:Rule)-[:HAS_DEADLINE]->(d:Deadline) RETURN DISTINCT d.label, d.amount, d.unit, d.anchor ORDER BY d.ord` |
| `precedent_lookup` | `MATCH (p:Precedent {outcome_class:$oc})-[:ANALOGOUS_TO]->(:Clause {id:$clid}) RETURN p.id, p.year, p.outcome_class ORDER BY p.year DESC LIMIT $n` plus `MATCH (:Clause {id:$clid})-[:LIMITED_BY]->(r:Rule)<-[:BEARS_ON]-(p:Precedent) ...` for precedents that share a rule |
| `rule_catalog` | `MATCH (r:Rule) WHERE $j IS NULL OR r.jurisdiction = $j RETURN r.id, r.name, r.citation, r.source_url, r.verification ORDER BY r.id` |

## Graph map notes

Ten labels and thirteen relationship types in total. `Meta` is a bookkeeping node holding the seed revision. Every call's real query, parameters, row count and latency is shown in the app under "show my working".

`precedent_lookup` key query (moved from the README):

```cypher
MATCH (:Clause {id:$clid})-[:LIMITED_BY]->(r:Rule)<-[:BEARS_ON]-(p:Precedent)-[:ANALOGOUS_TO]->(c2:Clause)
WHERE c2.id <> $clid RETURN p.id, p.year, p.outcome_class
```
