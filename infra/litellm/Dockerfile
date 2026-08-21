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
COPY start.sh /app/start.sh

# Railway injects PORT and probes that exact port. The base image defaults to
# 4000 and an exec-form CMD cannot expand ${PORT}, so use a tiny wrapper that
# keeps the base entrypoint while resolving the runtime port. LiteLLM then
# performs the Prisma migrations before it starts accepting HTTP requests.
ENTRYPOINT ["/bin/sh", "/app/start.sh"]
CMD []
