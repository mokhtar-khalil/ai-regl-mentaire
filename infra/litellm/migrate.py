"""Apply LiteLLM's Prisma migrations before the proxy container starts."""

import os

from litellm_proxy_extras.utils import ProxyExtrasDBManager


database_url = os.getenv("DATABASE_URL") or os.getenv("LITELLM_DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL or LITELLM_DATABASE_URL must be set")

# Prisma reads DATABASE_URL directly. The proxy normally resolves the custom
# config.yaml setting into it, but this standalone pre-deploy process does not
# load the proxy config.
os.environ["DATABASE_URL"] = database_url

if not ProxyExtrasDBManager.setup_database(
    use_migrate=True,
    use_v2_resolver=True,
):
    raise SystemExit("LiteLLM database migration failed")
