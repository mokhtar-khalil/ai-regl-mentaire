# Bakes infra/litellm/config.yaml into the official LiteLLM image — Railway's
# plain "Deploy from Docker Image" flow has no way to inject a repo file into
# a pre-built public image, so this service deploys from the repo instead,
# with Root Directory set to infra/litellm.
FROM ghcr.io/berriai/litellm:main-stable

COPY config.yaml /app/config.yaml

# Same Railway gotcha as the API's own Dockerfile: PORT is assigned
# dynamically and healthchecked on that port, not a hardcoded one.
ENV PORT=4000
# Override the base image's ENTRYPOINT explicitly rather than relying on
# how it combines with CMD — avoids guessing whether it already wraps
# `litellm` and would otherwise double up or swallow our args.
ENTRYPOINT []
CMD ["sh", "-c", "litellm --config /app/config.yaml --port ${PORT}"]
