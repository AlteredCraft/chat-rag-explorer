"""
Unit tests for error_messages.py.

Verifies that low-level provider errors translate into actionable,
user-facing messages that name the setting to fix.
"""
import httpx
import openai
import requests

from chat_rag_explorer.error_messages import (
    describe_chat_error,
    describe_model_list_error,
    missing_api_key_message,
)
from chat_rag_explorer.providers import Provider

PROVIDER = Provider(
    name="openrouter",
    base_url="https://openrouter.ai/api/v1",
    api_key="test-key",
)


def _openai_status_error(status_code):
    """Build a real openai.APIStatusError carrying the given HTTP status."""
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return openai.APIStatusError("upstream error", response=response, body=None)


def _requests_http_error(status_code):
    """Build a requests.HTTPError carrying the given HTTP status."""
    response = requests.models.Response()
    response.status_code = status_code
    return requests.exceptions.HTTPError("upstream error", response=response)


class TestMissingApiKeyMessage:
    """Tests for missing_api_key_message()."""

    def test_names_env_var_and_provider(self):
        """Message points at the provider's .env variable."""
        message = missing_api_key_message(PROVIDER)

        assert "openrouter" in message
        assert "OPENROUTER_API_KEY" in message
        assert ".env" in message

    def test_unknown_provider_falls_back_to_generic_wording(self):
        """A provider without an env-var mapping still gets a usable message."""
        provider = Provider(name="someprovider", base_url="http://x", api_key=None)

        message = missing_api_key_message(provider)

        assert "someprovider" in message
        assert "provider API key" in message


class TestDescribeChatError:
    """Tests for describe_chat_error()."""

    def test_connection_error_names_base_url(self):
        """Connection failures point at the base URL setting."""
        exc = openai.APIConnectionError(
            request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        )

        message = describe_chat_error(exc, PROVIDER)

        assert PROVIDER.base_url in message
        assert "OPENROUTER_BASE_URL" in message

    def test_401_names_api_key_env_var(self):
        """An auth failure points at the API key setting."""
        message = describe_chat_error(_openai_status_error(401), PROVIDER)

        assert "401" in message
        assert "OPENROUTER_API_KEY" in message

    def test_402_mentions_credits(self):
        """Insufficient credits explains how to proceed."""
        message = describe_chat_error(_openai_status_error(402), PROVIDER)

        assert "credits" in message

    def test_404_names_the_model(self):
        """A missing model names the model and points at Settings."""
        message = describe_chat_error(_openai_status_error(404), PROVIDER, model="vendor/gone")

        assert "vendor/gone" in message
        assert "Settings" in message

    def test_429_mentions_rate_limit(self):
        """Rate limiting suggests waiting and retrying."""
        message = describe_chat_error(_openai_status_error(429), PROVIDER)

        assert "rate limit" in message.lower()

    def test_unrecognized_error_falls_back_to_raw_message(self):
        """Errors without a misconfiguration story pass through unchanged."""
        message = describe_chat_error(RuntimeError("boom"), PROVIDER)

        assert message == "boom"


class TestDescribeModelListError:
    """Tests for describe_model_list_error()."""

    def test_connection_error_names_base_url(self):
        """Connection failures point at the base URL setting."""
        exc = requests.exceptions.ConnectionError("refused")

        message = describe_model_list_error(exc, PROVIDER)

        assert PROVIDER.base_url in message
        assert "OPENROUTER_BASE_URL" in message

    def test_timeout_names_base_url(self):
        """Timeouts get the same connection guidance."""
        exc = requests.exceptions.Timeout("timed out")

        message = describe_model_list_error(exc, PROVIDER)

        assert "OPENROUTER_BASE_URL" in message

    def test_401_names_api_key_env_var(self):
        """An auth failure points at the API key setting."""
        message = describe_model_list_error(_requests_http_error(401), PROVIDER)

        assert "401" in message
        assert "OPENROUTER_API_KEY" in message

    def test_unrecognized_error_includes_raw_message(self):
        """Errors without a misconfiguration story keep the raw detail."""
        message = describe_model_list_error(RuntimeError("kaput"), PROVIDER)

        assert "openrouter" in message
        assert "kaput" in message
