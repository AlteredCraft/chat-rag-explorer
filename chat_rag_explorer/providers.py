"""
LLM provider abstraction.

Every supported provider speaks the OpenAI-compatible chat completions
API, so the streaming path in services.py is provider-agnostic (the
OpenAI SDK pointed at a base URL). What actually varies per provider:

- Connection details: base URL and API key. A local Ollama needs no real
  key, but the OpenAI SDK requires a non-empty string, so such a provider
  would use a placeholder value like "ollama".
- Model listing: the endpoint and response schema differ per provider.

list_models() implementations must normalize each model dict to include
at least the fields the frontend consumes:

    id, name, context_length, pricing

Adding a provider (e.g. Ollama local or cloud) means extending
get_active_provider() with a selection switch and adding a
_list_<provider>_models() function here - the chat streaming code
does not change.
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Provider:
    """Connection details for an OpenAI-compatible LLM provider."""

    name: str
    base_url: str
    api_key: Optional[str]


def get_active_provider():
    """Build the active provider from app config.

    OpenRouter is the only provider today. When more are added, this is
    where a provider-selection config switch would live.

    Returns:
        Provider for the currently configured LLM backend
    """
    return Provider(
        name="openrouter",
        base_url=current_app.config["OPENROUTER_BASE_URL"],
        api_key=current_app.config.get("OPENROUTER_API_KEY"),
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
    raise ValueError(f"Unknown provider: {provider.name}")


def _list_openrouter_models(provider, request_id=None):
    """Fetch models from the OpenRouter API.

    OpenRouter's response already contains the normalized fields
    (id, name, context_length, pricing), so entries pass through as-is.
    """
    req_id = request_id or "no-id"
    start_time = time.time()

    url = f"{provider.base_url}/models"
    headers = {"Authorization": f"Bearer {provider.api_key}"}

    logger.debug(f"[{req_id}] GET {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        elapsed = time.time() - start_time
        logger.debug(f"[{req_id}] OpenRouter API response: {response.status_code} ({elapsed:.3f}s)")

        response.raise_for_status()
        return response.json().get("data", [])

    except requests.RequestException as e:
        elapsed = time.time() - start_time
        status_code = getattr(getattr(e, 'response', None), 'status_code', 'N/A')
        logger.error(
            f"[{req_id}] Failed to fetch models - Status: {status_code}, "
            f"Error: {type(e).__name__}: {str(e)} ({elapsed:.3f}s)",
            exc_info=True
        )
        raise
