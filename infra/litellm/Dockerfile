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
COPY migrate.py /app/migrate.py
COPY start.sh /app/start.sh

# Railway injects PORT and probes that exact port. The base image defaults to
# 4000 and an exec-form CMD cannot expand ${PORT}, so use a tiny wrapper that
# keeps the base entrypoint while resolving the runtime port.
#
# Database migrations run in Railway's separate pre-deploy container (see
# railway.toml). Running Prisma and the proxy together exceeds the service's
# 1 GiB memory limit during startup, so the long-running proxy must not try to
# update the schema again.
ENV DISABLE_SCHEMA_UPDATE=true

# Reset the base image entrypoint so Railway can replace CMD with the
# pre-deploy migration command. With no override, the normal service still
# starts through the port-aware wrapper.
ENTRYPOINT []
CMD ["/bin/sh", "/app/start.sh"]
