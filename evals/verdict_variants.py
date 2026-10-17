"""(c) Verdict-logic sanity: 4 base checks on the two synthetic cases + 13 hand-built variants (V15-V17 test the pasted-text clause matcher on ambiguous wording).
EXPECTED verdicts were written from the rule text BEFORE running (rule basis in each row). Each variant re-seeds a throwaway FalkorDB graph
with patched sample data and runs the real agent (agent.analyze), so this tests the graph queries + evaluation code, not a mock."""
import copy, os, shutil, socket, subprocess, sys, tempfile, time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
TODAY = "2026-10-17"
PED = "Claim repudiated: pre-existing disease under the waiting period"
# (id, case, patch, assume, text, expected, rule basis)
VARIANTS = [
    ("V01", "IN-01", {}, [], "", "undecidable", "43 months of cover < 60-month moratorium; earlier ported cover unproven -> cannot decide (IRDAI MC 2024)"),
    ("V02", "IN-01", {}, ["prior_cover_start"], "", "likely_contestable", "with proof of cover since 2018-04-01 = 100 months >= 60"),
    ("V03", "US-01", {}, [], "", "undecidable", "45 CFR 149.110: emergency services need no prior auth, but no record shows the CT was ordered in the ED"),
    ("V04", "US-01", {}, ["ed_encounter_record"], "", "likely_contestable", "ED record shows CT ordered in the emergency department"),
    ("V05", "IN-01", {"cover_start": "2019-01-15"}, [], "", "likely_contestable", "cover since 2019-01-15 = 91 months >= 60"),
    ("V06", "IN-01", {"cover_start": "2021-08-12"}, [], "", "likely_contestable", "exactly 60 complete months at claim date 2026-08-12 meets 'after 60 months'"),
    ("V07", "IN-01", {"cover_start": "2021-08-13"}, [], "", "undecidable", "59 months 30 days < 60 and prior cover unproven"),
    ("V08", "IN-01", {}, [], PED, "likely_contestable", "PED clause: waiting period capped at 36 months; 43 months of cover > 36"),
    ("V09", "IN-01", {"cover_start": "2024-06-01"}, [], PED, "undecidable", "26 months < 36 but earlier continuous cover (portability credit) not ruled out"),
    ("V10", "IN-01", {"cover_start": "2024-06-01"}, ["prior_cover_start"], PED, "likely_contestable", "26 months here + proven cover since 2018 -> credit carries over, > 36"),
    ("V11", "IN-01", {}, [], "Claim rejected: cosmetic surgery is excluded", "likely_valid", "cosmetic exclusion: no rule in the graph limits it"),
    ("V12", "US-01", {}, [], "Denied: not medically necessary under clinical criteria", "likely_valid", "medical-necessity denial: only a procedural rule (notice) applies, nothing bars the clause"),
    ("V13", "US-01", {}, [], "Denied: cosmetic, improves appearance", "likely_valid", "cosmetic exclusion: no rule limits it"),
    ("V15", "IN-01", {}, [], "Claim rejected: pre-existing diabetes was not disclosed in the proposal form (non-disclosure of material fact)", "undecidable", "text is a non-disclosure ground (clause 7.2), same facts as V01"),
    ("V16", "IN-01", {}, [], "Claim rejected: hypertension is subject to a 36 months waiting period", "likely_contestable", "waiting-period ground (clause 4.1); 43 months of cover > 36-month cap"),
    ("V17", "IN-01", {}, [], "Claim reduced: room rent above eligible limit, proportionate deduction applied", "likely_valid", "room-rent clause: no rule in the graph bars it"),
    ("V14", "US-01", {"ed_record": True}, [], "", "likely_contestable", "evidence now proves the CT was ordered during the ED visit"),
]


def _server():
    import redislite
    binp = os.path.join(os.path.dirname(redislite.__file__), "bin")
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    d = tempfile.mkdtemp()
    p = subprocess.Popen([os.path.join(binp, "redis-server"), "--port", str(port), "--loadmodule", os.path.join(binp, "falkordb.so"), "--dir", d, "--save", ""],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import redis
    for _ in range(60):
        try: redis.Redis(port=port).ping(); break
        except Exception: time.sleep(0.1)
    return p, port, d


def run():
    try:
        p, port, d = _server()
    except Exception as e:  # falkordblite missing
        return None, f"skipped: {e}"
    try:
        os.environ.update(FALKORDB_HOST="127.0.0.1", FALKORDB_PORT=str(port), CLAIMPATH_GRAPH="claimpath_eval")
        import seed, data, agent
        base = {k: copy.deepcopy(getattr(data, k)) for k in ("EVIDENCE",)}
        out = []
        for vid, case, patch, assume, text, expected, basis in VARIANTS:
            data.EVIDENCE = copy.deepcopy(base["EVIDENCE"])
            for e in data.EVIDENCE:
                if "cover_start" in patch and e["id"] == "EV-IN-1":
                    e["proves"] = [("current_cover_start", patch["cover_start"])]
            if patch.get("ed_record"):
                data.EVIDENCE.append(dict(id="EV-US-X", case_id="US-01", kind="document", label="ED record: CT ordered in ED", doc="ED summary", date="2026-07-03", proves=[("ed_encounter_record", "ED CT order")]))
            db = seed.connect(); seed.seed(db); g = db.select_graph(seed.GRAPH)
            r = agent.analyze(case, assume, text, TODAY, lambda q, pr=None: g.query(q, pr or {}).result_set)
            out.append(dict(id=vid, case=case, assume=assume, text=text[:40], expected=expected, got=r["verdict"]["code"], ok=expected == r["verdict"]["code"], basis=basis))
        data.EVIDENCE = base["EVIDENCE"]
        return out, None
    finally:
        p.terminate(); p.wait(); shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    res, err = run()
    print(err or "\n".join(f"{r['id']} {r['case']} expected={r['expected']} got={r['got']} {'OK' if r['ok'] else 'FAIL'}" for r in res))
