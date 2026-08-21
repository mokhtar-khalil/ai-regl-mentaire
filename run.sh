#!/bin/bash
# Launch the API (FastAPI) and the frontend (Next.js, dev mode) together
# for local verification. Use ./run-prod.sh instead to test the production
# build (next build + next start, no --reload).
# Usage: ./run.sh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "No .venv found — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    NODE_BIN="$(ls -d "$HOME"/tools/node-v*-darwin-*/bin 2>/dev/null | head -1)"
    if [ -z "$NODE_BIN" ]; then
        echo "Node.js not found on PATH and no portable install in ~/tools — install Node first."
        exit 1
    fi
    export PATH="$NODE_BIN:$PATH"
fi

if [ ! -d frontend/node_modules ]; then
    echo "Installing frontend dependencies..."
    npm --prefix frontend install
fi

API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
API_PID=""
FRONTEND_PID=""

cleanup() {
    echo "Stopping..."
    [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    true
}
trap cleanup EXIT INT TERM

echo "Starting API on :${API_PORT}..."
PYTHONPATH=. .venv/bin/uvicorn app.main:app --port "$API_PORT" &
API_PID=$!

# Wait for the API to be ready before starting the frontend.
for _ in $(seq 1 30); do
    if curl -s -o /dev/null "http://127.0.0.1:${API_PORT}/health"; then
        break
    fi
    sleep 1
done

echo "Starting frontend on :${FRONTEND_PORT} (next dev)..."
RAG_API_URL="http://127.0.0.1:${API_PORT}" PORT="$FRONTEND_PORT" npm --prefix frontend run dev &
FRONTEND_PID=$!

wait "$FRONTEND_PID"
