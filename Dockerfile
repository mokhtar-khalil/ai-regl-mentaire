# Production image for the FastAPI RAG API (app/main.py).
# Runs on Python 3.12 regardless of the host's Python version — sidesteps
# the local dev machine's Python 3.9 (EOL) constraints entirely.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY app ./app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Railway assigns PORT dynamically and healthchecks whatever port that is —
# a container listening on a different, hardcoded port fails the network
# healthcheck even though the app itself is running fine.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
