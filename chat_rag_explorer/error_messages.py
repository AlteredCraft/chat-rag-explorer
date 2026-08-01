"""
User-facing messages for provider misconfiguration and failure states.

Raw errors from the OpenAI SDK or requests are accurate but cryptic
("Error code: 401 - {'error': {...}}"). This module translates the
failure states a user can actually fix - a bad API key, a wrong base
URL, an unreachable service, a missing model - into plain-language
messages that say what went wrong and where to fix it.

The env-var maps are keyed by provider name so adding a provider only
needs new entries here, alongside the new branch in
providers.get_active_provider().
"""
import openai
import requests

# Where each provider's connection settings live in .env - used to point
# the user at the exact setting to fix.
API_KEY_ENV_VARS = {"openrouter": "OPENROUTER_API_KEY", "ollama": "OLLAMA_API_KEY"}
BASE_URL_ENV_VARS = {"openrouter": "OPENROUTER_BASE_URL", "ollama": "OLLAMA_BASE_URL"}


def missing_api_key_message(provider):
    """Message for the no-API-key-configured state.

    Args:
        provider: The active Provider (see providers.py)

    Returns:
        Actionable message naming the .env variable to set
    """
    env_var = API_KEY_ENV_VARS.get(provider.name, "the provider API key")
    return (
        f"No API key is configured for {provider.name}. "
        f"Set {env_var} in your .env file and restart the app."
    )


def describe_chat_error(exc, provider, model=None):
    """Translate a chat-streaming exception into an actionable message.

    Args:
        exc: The exception raised while streaming from the OpenAI SDK
        provider: The active Provider
        model: Optional model ID the request targeted (improves 404 text)

    Returns:
        A user-facing message; falls back to str(exc) when the error
        isn't a recognized misconfiguration state
    """
    if isinstance(exc, openai.APIConnectionError):
        return _connection_message(provider)

    # openai.APIStatusError subclasses carry the HTTP status directly
    status = getattr(exc, "status_code", None)
    return _describe_by_status(status, provider, model) or str(exc)


def describe_model_list_error(exc, provider):
    """Translate a model-listing failure into an actionable message.

    Args:
        exc: The exception raised while fetching the model catalog
        provider: The active Provider

    Returns:
        A user-facing message describing the likely misconfiguration
    """
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return _connection_message(provider)

    # requests.HTTPError carries the status on its response object
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    described = _describe_by_status(status, provider)
    if described:
        return described
    return f"Could not load models from {provider.name}: {exc}"


def _connection_message(provider):
    """Message for connection failures (wrong base URL, service down)."""
    env_var = BASE_URL_ENV_VARS.get(provider.name, "the provider base URL")
    message = (
        f"Could not reach {provider.name} at {provider.base_url}. "
        f"Check {env_var} in your .env file and that the service is reachable."
    )
    if provider.name == "ollama":
        message += " Is Ollama running? Start it with 'ollama serve'."
    return message


def _describe_by_status(status, provider, model=None):
    """Map well-known HTTP status codes to actionable messages.

    Returns None for statuses without a specific misconfiguration story,
    so callers can fall back to the raw error.
    """
    key_env_var = API_KEY_ENV_VARS.get(provider.name, "the provider API key")

    if status == 401:
        return (
            f"{provider.name} rejected the API key (HTTP 401). "
            f"Check that {key_env_var} in your .env file is a valid, active key."
        )
    if status == 402:
        return (
            f"{provider.name} reports insufficient credits (HTTP 402). "
            f"Add credits to your account or select a free model in Settings."
        )
    if status == 403:
        return (
            f"{provider.name} denied access (HTTP 403). "
            f"The API key may not have permission for this request."
        )
    if status == 404:
        target = f"model '{model}'" if model else "requested resource"
        return (
            f"{provider.name} could not find the {target} (HTTP 404). "
            f"Select a different model in Settings."
        )
    if status == 429:
        return (
            f"{provider.name} rate limit exceeded (HTTP 429). "
            f"Wait a moment and try again."
        )
    return None
