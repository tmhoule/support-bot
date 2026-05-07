import os

# Ensure required env vars are present at import time so that modules which
# instantiate Settings on import (e.g. app.main) succeed during test collection.
_TEST_ENV_DEFAULTS = {
    "LITELLM_BASE_URL": "x",
    "LITELLM_API_KEY": "x",
    "LITELLM_CHAT_MODEL": "x",
    "LITELLM_EMBEDDING_MODEL": "x",
    "GITHUB_REPO_URL": "x",
    "GITHUB_TOKEN": "x",
    "ADMIN_TOKEN": "x",
    "SESSION_SECRET": "x" * 32,
}

for _k, _v in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)
