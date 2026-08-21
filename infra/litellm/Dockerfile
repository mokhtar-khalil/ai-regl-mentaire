# Bakes infra/litellm/config.yaml into the official LiteLLM image — Railway's
# plain "Deploy from Docker Image" flow has no way to inject a repo file into
# a pre-built public image, so this service deploys from the repo instead,
# with Root Directory set to infra/litellm.
#
# litellm-database (not plain litellm): the plain image's main-stable tag has
# a known, unresolved upstream bug on its "wolfi" base — Prisma's query
# engine can't find the OpenSSL version it needs, so DB-backed features fail
# with "Not connected to the query engine" / "No connected db" (BerriAI/
# litellm#17093, closed "not planned"). litellm-database is built for exactly
# this DB-backed use case and doesn't hit it.
FROM ghcr.io/berriai/litellm-database:main-stable

COPY config.yaml /app/config.yaml

# Keep the base image's own ENTRYPOINT (docker/prod_entrypoint.sh) — it
# does required setup (Prisma migrations for the spend-logs DB, etc.)
# before starting the server. Overriding it with a bare `litellm ...`
# command skipped that setup and the container died silently. Only
# override CMD, the same shape as the base image's own default
# (["--port", "4000"]), just adding --config.
#
# Port is fixed at 4000 (not Railway's dynamic $PORT) because CMD's exec
# form can't do shell variable expansion, and the entrypoint script's own
# argument parsing can't be assumed to support it either — set this
# service's target port to 4000 in Railway's dashboard instead of relying
# on the container reading $PORT.
CMD ["--config", "/app/config.yaml", "--port", "4000"]
