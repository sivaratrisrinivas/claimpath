"""Vercel entrypoint. FalkorDB is the only database: set FALKORDB_HOST/PORT/USERNAME/PASSWORD (/SSL=1) to a hosted FalkorDB.
On cold start the graph is (re)seeded only when the stored data revision differs (guarded by a short graph lock so concurrent
cold starts don't double-seed). The lock is a graph, because a hosted FalkorDB user may not be allowed raw Redis SET."""
import os, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "backend"))
import seed, data  # noqa: E402


def _current(g):
    try:
        return g.ro_query("MATCH (m:Meta {id: 'rev'}) RETURN m.rev").result_set[0][0] == data.REV
    except Exception:
        return False


def ensure_seeded():
    try:
        db = seed.connect()
        g = db.select_graph(seed.GRAPH)
        if _current(g):
            return
        lg = db.select_graph(seed.GRAPH + "_lock")
        tok = os.urandom(6).hex()
        try:
            lg.query("MATCH (l:L) WHERE timestamp() - l.t > 60000 DELETE l")
        except Exception:
            pass
        got = lg.query("MERGE (l:L {id: 1}) ON CREATE SET l.t = timestamp(), l.o = $tok RETURN l.o", {"tok": tok}).result_set[0][0] == tok
        if got:
            try:
                seed.seed(db)
            finally:
                try: lg.delete()
                except Exception: pass
        else:
            for _ in range(60):
                time.sleep(0.5)
                if _current(g):
                    return
    except Exception as e:
        print("ensure_seeded failed:", repr(e), file=sys.stderr)


ensure_seeded()
from app import app  # noqa: E402,F401
