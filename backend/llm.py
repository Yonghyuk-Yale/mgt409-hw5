"""The one model every agent uses: gpt-6-luna through the Portkey gateway.

HW 5 rule: only gpt-6-luna, for every agent. The name is fixed here; if PORTKEY_MODEL is set
to anything else the team refuses to start instead of quietly running another model.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

HERE = Path(__file__).resolve().parent

# A project-local .env wins; the repo-root .env still applies.
for _directory in (HERE, *HERE.parents):
    _env_file = _directory / ".env"
    if _env_file.is_file():
        load_dotenv(_env_file, override=False)

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
REQUEST_TIMEOUT = 45.0  # seconds per model call


class TeamUnavailable(RuntimeError):
    """The team cannot run (missing key or a model other than gpt-6-luna)."""


@lru_cache(maxsize=1)
def get_model() -> OpenAIResponsesModel:
    configured = os.getenv("PORTKEY_MODEL") or MODEL_NAME
    if configured != MODEL_NAME:
        raise TeamUnavailable(f"PORTKEY_MODEL must be {MODEL_NAME} for HW 5.")
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise TeamUnavailable("PORTKEY_API_KEY is not set in .env.")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
        timeout=REQUEST_TIMEOUT,
    )
    # Responses API: on Portkey, this model rejects function tools on chat completions (found in HW 4).
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
