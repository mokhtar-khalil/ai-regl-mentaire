#!/bin/bash
# Launch the API (FastAPI) and the test UI (Gradio) together.
# Usage: ./run.sh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "No .venv found — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

API_PORT="${API_PORT:-8000}"
export RAG_API_URL="http://127.0.0.1:${API_PORT}"

cleanup() {
    echo "Stopping..."
    kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API on :${API_PORT}..."
PYTHONPATH=. .venv/bin/uvicorn app.main:app --port "$API_PORT" &
API_PID=$!

# Wait for the API to be ready before starting the UI.
for _ in $(seq 1 30); do
    if curl -s -o /dev/null "http://127.0.0.1:${API_PORT}/health"; then
        break
    fi
    sleep 1
done

echo "Starting Gradio UI..."
PYTHONPATH=. .venv/bin/python gradio_app.py
