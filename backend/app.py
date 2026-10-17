"""ClaimPath API. FalkorDB is the only store and the only reasoning substrate: every endpoint calls graph tools (tools.py).
If FalkorDB is unreachable the API answers 503."""
import os, sys, json, datetime as dt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
import seed as seedmod, tools as T, agent, mcp, data

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
app = FastAPI(title="ClaimPath")


class DBDown(Exception):
    pass


_CONN = {}  # one reused connection: a remote hosted FalkorDB makes reconnect+ping per call slow


def _key():
    return tuple(os.environ.get(k) for k in ("FALKORDB_HOST", "FALKORDB_PORT", "FALKORDB_USERNAME", "CLAIMPATH_GRAPH"))


def graph():
    try:
        k = _key()
        db = _CONN.get(k)
        if db is None:
            db = seedmod.connect()
            db.connection.ping()
            _CONN[k] = db
        return db.select_graph(seedmod.GRAPH)
    except Exception as e:
        _CONN.pop(_key(), None)
        raise DBDown(str(e))


def run(query, params=None):
    try:
        return graph().query(query, params or {}).result_set
    except DBDown:
        raise
    except Exception as e:
        msg = str(e)
        if "Connection" in type(e).__name__ or "connect" in msg.lower() or "Timeout" in type(e).__name__:
            _CONN.pop(_key(), None)
            raise DBDown(msg)
        raise


@app.exception_handler(DBDown)
async def db_down(_: Request, exc: DBDown):
    return JSONResponse(status_code=503, content={"error": "FalkorDB unavailable", "cause": str(exc)[:200]})


class AnalyzeReq(BaseModel):
    case_id: str
    assume: list[str] = []
    text: str = ""
    today: str | None = None


@app.get("/api/cases")
def cases():
    rows = run("MATCH (c:Case) RETURN c.id, c.country, c.title, c.summary, c.insurer, c.currency ORDER BY c.id")
    return [dict(id=r[0], country=r[1], title=r[2], summary=r[3], insurer=r[4], currency=r[5]) for r in rows]


@app.post("/api/analyze")
def analyze(req: AnalyzeReq):
    if req.case_id not in {c["id"] for c in data.CASES}:
        raise HTTPException(404, "Unknown sample case")
    today = req.today or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(today)
    except ValueError:
        raise HTTPException(400, "today must be YYYY-MM-DD")
    return agent.analyze(req.case_id, req.assume[:5], req.text[:2000], today, run)


@app.get("/api/tools")
def tools_list():
    return mcp.tool_list()


@app.post("/api/tool/{name}")
async def tool_call(name: str, request: Request):
    if name not in T.TOOLS:
        raise HTTPException(404, "Unknown tool")
    args = await request.json() if (await request.body()) else {}
    try:
        return T.call_tool(name, args, run)
    except TypeError as e:
        raise HTTPException(400, str(e))


@app.get("/mcp")
def mcp_info():
    return {"name": "claimpath", "transport": "streamable-http (POST JSON-RPC)", "tools": [t["name"] for t in mcp.tool_list()]}


@app.post("/mcp")
async def mcp_rpc(request: Request):
    try:
        msg = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status_code=400)
    if isinstance(msg, list):
        out = [r for r in (mcp.handle(m, run) for m in msg) if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)
    res = mcp.handle(msg, run)
    return Response(status_code=202) if res is None else JSONResponse(res)


@app.get("/api/health")
def health():
    n = run("MATCH (n) RETURN count(n)")[0][0]
    rev = run("MATCH (m:Meta {id:'rev'}) RETURN m.rev")
    return {"ok": True, "graph": seedmod.GRAPH, "nodes": n, "rev": rev[0][0] if rev else None,
            "rules": run("MATCH (r:Rule) RETURN count(r)")[0][0], "falkordb": "connected"}


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
