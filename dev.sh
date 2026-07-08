#!/usr/bin/env bash
# Launch backend (:8000) and frontend (:5173) together for local development.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "▶ backend  → http://localhost:8000"
( cd "$ROOT/backend" && uv run uvicorn api.main:app --port 8000 ) &

echo "▶ frontend → http://localhost:5173"
( cd "$ROOT/frontend" && npm run dev ) &

wait
