"""Tests run against a real FalkorDB (falkordblite, started by conftest)."""
import json


def analyze(client, case, assume=(), text=""):
    r = client.post("/api/analyze", json={"case_id": case, "assume": list(assume), "text": text, "today": "2026-10-17"})
    assert r.status_code == 200, r.text
    return r.json()


def test_health_and_cases(client):
    h = client.get("/api/health").json()
    assert h["ok"] and h["rules"] == 10 and h["nodes"] > 50
    assert {c["id"] for c in client.get("/api/cases").json()} == {"IN-01", "US-01"}


def test_india_flip_on_prior_cover_proof(client):
    a = analyze(client, "IN-01")
    assert a["verdict"]["code"] == "undecidable"
    assert [m["key"] for m in a["missing"]] == ["prior_cover_start"]
    b = analyze(client, "IN-01", ["prior_cover_start"])
    assert b["verdict"]["code"] == "likely_contestable"
    assert b["strongest"]["id"] == "R-IN-MORATORIUM"
    assert b["strongest"]["eval"]["months"] == 100
    assert b["missing"] == [] and "WHAT-IF" in json.dumps(b["strongest"]["facts"])
    assert "[CONFIRM AND ATTACH" in b["letter"]["text"]


def test_us_flip_on_ed_record(client):
    a = analyze(client, "US-01")
    assert a["verdict"]["code"] == "undecidable" and a["missing"][0]["key"] == "ed_encounter_record"
    b = analyze(client, "US-01", ["ed_encounter_record"])
    assert b["verdict"]["code"] == "likely_contestable" and b["strongest"]["id"] == "R-US-EMERG"


def test_likely_valid_paths(client):
    a = analyze(client, "IN-01", text="Claim declined: cosmetic procedure excluded")
    assert a["clause"]["id"] == "IN-9.1" and a["verdict"]["code"] == "likely_valid"
    b = analyze(client, "US-01", text="Not medically necessary per our criteria")
    assert b["clause"]["id"] == "US-3.5" and b["verdict"]["code"] == "likely_valid"
    assert "Procedural" in " ".join(b["verdict"]["because"])


def test_bill_reconciliation(client):
    a = analyze(client, "IN-01")["bill"]
    assert a["total_billed"] == 318500 and a["room_rent"]["eligible_per_day"] == 5000
    assert a["proportionate_deduction"] == round(125000 * (1 - 5000 / 7500))
    u = analyze(client, "US-01")["bill"]
    assert u["denied_total"] == 3850 and len(u["denied_lines"]) == 1


def test_deadlines_and_escalation(client):
    a = analyze(client, "IN-01")
    d = {x["id"]: x for x in a["clock"]["deadlines"]}
    assert d["D-IN-4"]["due"] == "2027-09-28" and d["D-IN-1"]["due"] == "2026-10-31"
    assert [p["id"] for p in a["escalation"]["path"]][-1] == "R-IN-OMB" and a["escalation"]["hops"] == 2
    u = analyze(client, "US-01")
    assert {x["id"]: x for x in u["clock"]["deadlines"]}["D-US-1"]["due"] == "2027-03-13"
    assert [p["id"] for p in u["escalation"]["path"]][-1] == "R-US-EXT"


def test_every_rule_has_source_and_trace_logs_cypher(client):
    a = analyze(client, "IN-01")
    assert all(c["source_url"].startswith("https://") for c in a["candidates"])
    names = [t["tool"] for t in a["trace"]]
    assert names == ["get_case", "rule_centrality", "strongest_rule_path", "missing_facts", "reconcile_bill", "escalation_path", "deadline_clock", "draft_letter"]
    assert all(t["cypher"] for t in a["trace"] if t["tool"] != "draft_letter")
    rules = client.post("/api/tool/rule_catalog", json={}).json()["result"]["rules"]
    assert len(rules) == 10 and all(r["source_url"] for r in rules)


def test_pagerank_runs_in_falkordb(client):
    r = client.post("/api/tool/rule_centrality", json={"jurisdiction": "IN"}).json()
    assert "algo.pageRank" in r["cypher"][0]["cypher"]
    top = r["result"]["ranking"][0]["rule"]
    assert top in ("R-IN-MORATORIUM", "R-IN-OMB")


def test_mcp(client):
    def rpc(m, i=1):
        return client.post("/mcp", json={"jsonrpc": "2.0", "id": i, "method": m[0], "params": m[1]})
    init = rpc(("initialize", {})).json()
    assert init["result"]["serverInfo"]["name"] == "claimpath"
    tl = rpc(("tools/list", {})).json()["result"]["tools"]
    assert {"strongest_rule_path", "missing_facts", "deadline_clock", "reconcile_bill", "escalation_path"} <= {t["name"] for t in tl}
    call = rpc(("tools/call", {"name": "missing_facts", "arguments": {"case_id": "IN-01", "clause_id": "IN-7.2"}})).json()["result"]
    assert not call["isError"] and "prior_cover_start" in call["content"][0]["text"]
    bad = rpc(("tools/call", {"name": "nope", "arguments": {}})).json()
    assert bad["error"]["code"] == -32602
    note = client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert note.status_code == 202


def test_assume_does_not_write(client):
    analyze(client, "IN-01", ["prior_cover_start"])
    assert analyze(client, "IN-01")["verdict"]["code"] == "undecidable"  # what-if is a query parameter, never persisted


def test_idempotent_seed(client, falkordb_server):
    import seed
    n1 = seed.seed()
    n2 = seed.seed()
    assert n1 == n2
