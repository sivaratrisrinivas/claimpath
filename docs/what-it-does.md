# What ClaimPath does

Back to the [README](../README.md).


ClaimPath takes one rejection and shows **one traceable path**, with a source link at every step:

> insurer's reason -> the policy clause it relies on -> what **your** evidence proves (dates, bill lines) -> the governing rule -> verdict

The verdict is one of **likely contestable**, **likely valid**, or **undecidable until X is found**, with the list of missing facts and where to look. You **drag the missing document onto the letter** (or tap it) and the verdict flips live. It then reconciles the hospital bill against the policy (India: room-rent proportionate deduction; US: denied EOB lines), starts the deadline clock, and drafts the appeal / grievance letter for you to send yourself.

ClaimPath never files anything and never contacts anyone. Sample cases are **synthetic** (one India, one USA); a separate panel shows 118 **real past decisions** (see below). The rules are real and each carries the URL of the official text. **Not legal or medical advice.**

## Run locally and hosted setup (full)

```bash
git clone https://github.com/sivaratrisrinivas/claimpath && cd claimpath
./scripts/run_local.sh        # starts falkordb/falkordb in Docker, seeds the graph, serves http://localhost:8000
# tests (real FalkorDB via falkordblite, no Docker needed):
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q
```

Hosted: set `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_USERNAME`, `FALKORDB_PASSWORD` (and `FALKORDB_SSL=1` if TLS). On cold start the graph is seeded idempotently with batched `UNWIND` writes, guarded by a lock *graph* (a hosted FalkorDB user may not be allowed raw `SET`), and one connection is reused across requests. The deployed instance is FalkorDB Cloud.
