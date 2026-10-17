#!/usr/bin/env bash
# Run ClaimPath locally in under 5 minutes. Needs Python 3.10+ and Docker (or any FalkorDB).
set -e
cd "$(dirname "$0")/.."
docker ps --format '{{.Names}}' | grep -q '^claimpath-falkordb$' || docker run -d --name claimpath-falkordb -p 6379:6379 falkordb/falkordb:latest
python3 -m venv .venv && .venv/bin/pip -q install -r requirements.txt
.venv/bin/python backend/seed.py
echo "Open http://localhost:8000"
exec .venv/bin/uvicorn index:app --app-dir . --port 8000
