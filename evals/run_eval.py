#!/usr/bin/env python3
"""ClaimPath accuracy check. Usage (from repo root):  python evals/run_eval.py [--split dev|test|all] [--verdicts]
  (a) clause/rule mapping accuracy of backend/classify.py on the 118 real precedents vs evals/labels.csv (hand labels, RUBRIC.md)
  (b) outcome-tag accuracy on the 58 India awards
  (c) verdict-logic sanity (needs falkordblite): evals/verdict_variants.py
The held-out TEST split is only evaluated with --split test/all; each such run is appended to evals/heldout_runs.log so reuse is visible."""
import csv, datetime, hashlib, json, math, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend")); sys.path.insert(0, HERE)
import classify as C

RULES = {"IN-7.2": {"R-IN-MORATORIUM", "R-IN-CITE"}, "IN-4.1": {"R-IN-PED36", "R-IN-CITE"}, "US-9.4": {"R-US-EMERG", "R-US-NOTICE"}, "US-3.5": {"R-US-NOTICE"}}
rules_of = lambda c: RULES.get(c, set())


def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def load():
    labels = {r["id"]: r for r in csv.DictReader(open(os.path.join(HERE, "labels.csv")))}
    cases = {}
    for l in open(os.path.join(HERE, "cases.jsonl")):
        r = json.loads(l); cases[r["id"]] = r
    return labels, cases


def predict(c):
    if c["jurisdiction"] == "IN":
        return C.india_clause(c["body"]) or "NONE", C.outcome_of(c["body"])
    return C.us_clause(c["treatment_category"], c["treatment_sub"], c["findings"], c["typ"]) or "NONE", None


def prf(pairs, classes):
    out = {}
    for k in classes:
        tp = sum(1 for t, p in pairs if t == k and p == k); fp = sum(1 for t, p in pairs if t != k and p == k); fn = sum(1 for t, p in pairs if t == k and p != k)
        out[k] = dict(support=sum(1 for t, _ in pairs if t == k), precision=round(tp / (tp + fp), 3) if tp + fp else None, recall=round(tp / (tp + fn), 3) if tp + fn else None, tp=tp, fp=fp, fn=fn)
    return out


def clause_eval(ids, labels, cases):
    res = {}
    for jur in ("IN", "US", "ALL"):
        sel = [i for i in ids if jur == "ALL" or labels[i]["jurisdiction"] == jur]
        pairs = [(labels[i]["true_clause"], predict(cases[i])[0]) for i in sel]
        ok = sum(t == p for t, p in pairs)
        rok = sum(rules_of(t) == rules_of(p) for t, p in pairs)
        conf = collections.Counter((t, p) for t, p in pairs if t != p)
        res[jur] = dict(n=len(pairs), clause_acc=round(ok / len(pairs), 3), clause_ci=wilson(ok, len(pairs)), rule_acc=round(rok / len(pairs), 3), rule_ci=wilson(rok, len(pairs)),
                        per_class=prf(pairs, sorted({t for t, _ in pairs} | {p for _, p in pairs})), errors=[dict(id=i, true=labels[i]["true_clause"], pred=predict(cases[i])[0]) for i in sel if labels[i]["true_clause"] != predict(cases[i])[0]],
                        confusion={f"{t}->{p}": n for (t, p), n in conf.items()})
    return res


def outcome_eval(ids, labels, cases):
    sel = [i for i in ids if labels[i]["jurisdiction"] == "IN"]
    dec = [(i, labels[i]["true_outcome"], predict(cases[i])[1]) for i in sel]
    pos = lambda p: p is not None and "succeeded" in p
    clear = [(i, t, p) for i, t, p in dec if t in ("CLAIMANT", "INSURER")]
    tp = sum(1 for _, t, p in clear if t == "CLAIMANT" and pos(p)); fn = sum(1 for _, t, p in clear if t == "CLAIMANT" and not pos(p))
    tn = sum(1 for _, t, p in clear if t == "INSURER" and not pos(p)); fp = sum(1 for _, t, p in clear if t == "INSURER" and pos(p))
    acc = (tp + tn) / len(clear) if clear else None
    return dict(n_all=len(dec), n_clear=len(clear), unclear_labelled=sum(1 for _, t, _ in dec if t == "UNCLEAR"), accuracy=round(acc, 3) if acc is not None else None, ci=wilson(tp + tn, len(clear)),
                TPR_claimant=round(tp / (tp + fn), 3) if tp + fn else None, TNR_insurer=round(tn / (tn + fp), 3) if tn + fp else None, tp=tp, fn=fn, tn=tn, fp=fp,
                errors=[dict(id=i, true=t, pred=p) for i, t, p in clear if (t == "CLAIMANT") != pos(p)], unclear_forced=[dict(id=i, pred=p) for i, t, p in dec if t == "UNCLEAR"])


def main():
    split_arg = "dev"; verdicts = "--verdicts" in sys.argv
    if "--split" in sys.argv: split_arg = sys.argv[sys.argv.index("--split") + 1]
    labels, cases = load(); sp = json.load(open(os.path.join(HERE, "split.json")))
    out = {"mapper_sha": hashlib.sha1(open(os.path.join(HERE, "..", "backend", "classify.py"), "rb").read()).hexdigest()[:10], "date": datetime.datetime.now().isoformat(timespec="seconds")}
    for name in (["dev", "test"] if split_arg == "all" else [split_arg]):
        if name == "test":
            open(os.path.join(HERE, "heldout_runs.log"), "a").write(f"{out['date']} mapper_sha={out['mapper_sha']} evaluated held-out test split\n")
        out[name] = dict(clause=clause_eval(sp[name], labels, cases), outcome=outcome_eval(sp[name], labels, cases))
    if verdicts:
        import verdict_variants as V
        res, err = V.run(); out["verdicts"] = dict(error=err, rows=res, passed=sum(r["ok"] for r in res) if res else None, n=len(res) if res else None)
    print(json.dumps(out, indent=1)); 
    if "--out" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--out") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
