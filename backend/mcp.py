"""Minimal MCP server over HTTP (JSON-RPC 2.0, stateless): initialize, tools/list, tools/call, ping.
The same tool registry as the UI agent. Point any MCP client that speaks streamable HTTP at POST /mcp."""
import json
import tools as T

PROTOCOL = "2025-03-26"


def tool_list():
    return [{"name": n, "description": t["desc"], "inputSchema": t["schema"]} for n, t in T.TOOLS.items()]


def handle(msg, runner):
    """Returns a JSON-RPC response dict, or None for notifications."""
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None and method and method.startswith("notifications/"):
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}
    if method == "initialize":
        return ok({"protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "claimpath", "version": "0.1.0"},
                   "instructions": "Graph tools over a FalkorDB claim-rejection knowledge graph. The two sample cases are synthetic; precedents are REAL public past decisions (India Ombudsman 2009-2012, California IMR 2024-2026). Not legal advice."})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": tool_list()})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in T.TOOLS:
            return err(-32602, f"Unknown tool {name}")
        try:
            out = T.call_tool(name, args, runner)
            payload = {"result": out["result"], "cypher": out["cypher"]}
            return ok({"content": [{"type": "text", "text": json.dumps(payload, default=str)}], "isError": False})
        except Exception as e:  # tool errors are reported in-band per MCP
            return ok({"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True})
    return err(-32601, f"Method not found: {method}")
