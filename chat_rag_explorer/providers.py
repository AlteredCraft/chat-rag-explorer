"""
LLM provider abstraction.

Every supported provider speaks the OpenAI-compatible chat completions
API, so the streaming path in services.py is provider-agnostic (the
OpenAI SDK pointed at a base URL). What actually varies per provider:

- Connection details: base URL and API key. Users set these once as
  LLM_BASE_URL and LLM_API_KEY; the per-provider fallbacks live in
  PROVIDER_DEFAULTS below.
- Model listing: the response schema differs per provider.

list_models() implementations must normalize each model dict to include
at least the fields the frontend consumes:

    id, name, context_length, pricing

Supported providers are OpenRouter (LLM_PROVIDER=openrouter) and Ollama
local or cloud (LLM_PROVIDER=ollama). LLM_PROVIDER is required and has
no default, so an unset value is an error rather than a silent choice.
Adding another provider means a new PROVIDER_DEFAULTS entry and a
_list_<provider>_models() function here - the chat streaming code does
not change.
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Per-provider connection defaults, used when LLM_BASE_URL / LLM_API_KEY
# are not set. Defaulting per provider rather than globally means the
# endpoint can never disagree with the selected provider - switching
# LLM_PROVIDER to ollama with no LLM_BASE_URL lands on a local Ollama,
# not on a stale OpenRouter URL.
#
# A local Ollama has no auth, but the OpenAI SDK requires a non-empty
# key, so it gets a placeholder. OpenRouter genuinely needs a real key,
# so it has none and an unset key reads as "not configured".
PROVIDER_DEFAULTS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": None,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    },
}

# Valid LLM_PROVIDER values. Startup validation (main.py) and the
# lookup below both check against this list.
SUPPORTED_PROVIDERS = tuple(PROVIDER_DEFAULTS)


@dataclass(frozen=True)
class Provider:
    """Connection details for an OpenAI-compatible LLM provider."""

    name: str
    base_url: str
    api_key: Optional[str]


def get_active_provider():
    """Build the active provider from app config.

    LLM_PROVIDER selects the provider. LLM_BASE_URL and LLM_API_KEY apply
    to whichever one is selected; each falls back to that provider's entry
    in PROVIDER_DEFAULTS when unset.

    Returns:
        Provider for the currently configured LLM backend

    Raises:
        ValueError: If LLM_PROVIDER is unset or names an unsupported
            provider. Callers on an error path should catch this rather
            than let it mask the failure they were already reporting.
    """
    provider_name = current_app.config.get("LLM_PROVIDER")

    if not provider_name:
        raise ValueError(
            f"LLM_PROVIDER is not set. Add it to your .env as one of: "
            f"{', '.join(SUPPORTED_PROVIDERS)}."
        )

    defaults = PROVIDER_DEFAULTS.get(provider_name)
    if defaults is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider_name}'. "
            f"Set LLM_PROVIDER in your .env to one of: {', '.join(SUPPORTED_PROVIDERS)}."
        )

    return Provider(
        name=provider_name,
        base_url=current_app.config.get("LLM_BASE_URL") or defaults["base_url"],
        api_key=current_app.config.get("LLM_API_KEY") or defaults["api_key"],
    )


def list_models(provider, request_id=None):
    """Fetch the provider's model catalog, normalized for the frontend.

    Args:
        provider: The Provider to query
        request_id: Optional request ID for log correlation

    Returns:
        List of model dicts, each containing at least id, name,
        context_length, and pricing
    """
    if provider.name == "openrouter":
        return _list_openrouter_models(provider, request_id)
    if provider.name == "ollama":
        return _list_ollama_models(provider, request_id)
    raise ValueError(f"Unknown provider: {provider.name}")


def _fetch_models_json(provider, request_id=None):
    """GET the provider's /models endpoint and return the parsed JSON.

    Both supported providers serve their model catalog at
    {base_url}/models with bearer-token auth (a local Ollama simply
    ignores the header), so the HTTP call, timing logs, and error
    handling live here. Normalizing the response is what actually
    differs per provider - that stays in _list_<provider>_models().
    """
    req_id = request_id or "no-id"
    start_time = time.time()

    url = f"{provider.base_url}/models"
    headers = {"Authorization": f"Bearer {provider.api_key}"}

    logger.debug(f"[{req_id}] GET {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        elapsed = time.time() - start_time
        logger.debug(f"[{req_id}] {provider.name} API response: {response.status_code} ({elapsed:.3f}s)")

        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        elapsed = time.time() - start_time
        status_code = getattr(getattr(e, 'response', None), 'status_code', 'N/A')
        logger.error(
            f"[{req_id}] Failed to fetch models - Status: {status_code}, "
            f"Error: {type(e).__name__}: {str(e)} ({elapsed:.3f}s)",
            exc_info=True
        )
        raise


def _list_openrouter_models(provider, request_id=None):
    """Fetch models from the OpenRouter API.

    OpenRouter's response already contains the normalized fields
    (id, name, context_length, pricing), so entries pass through as-is.
    """
    return _fetch_models_json(provider, request_id).get("data", [])


def _list_ollama_models(provider, request_id=None):
    """Fetch models from Ollama's OpenAI-compatible /models endpoint.

    Works for both a local Ollama (lists pulled models, no auth) and
    Ollama cloud (lists cloud models, real API key). Ollama's listing
    carries only model IDs like "llama3.2:3b", so the remaining
    normalized fields are filled in here: name mirrors the ID, the
    context length is not reported (the frontend shows "N/A"), and the
    empty pricing dict marks every model as free.
    """
    entries = _fetch_models_json(provider, request_id).get("data", [])
    return [
        {
            "id": entry["id"],
            "name": entry["id"],
            "context_length": None,
            "pricing": {},
        }
        for entry in entries
        if entry.get("id")
    ]
