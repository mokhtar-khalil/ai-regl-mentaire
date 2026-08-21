#!/bin/sh
set -eu

exec /app/docker/prod_entrypoint.sh \
    --config /app/config.yaml \
    --port "${PORT:-4000}"
