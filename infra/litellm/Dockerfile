# Bakes infra/litellm/config.yaml into the official LiteLLM image — Railway's
# plain "Deploy from Docker Image" flow has no way to inject a repo file into
# a pre-built public image, so this service deploys from the repo instead,
# with Root Directory set to infra/litellm.
FROM ghcr.io/berriai/litellm:main-stable

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
