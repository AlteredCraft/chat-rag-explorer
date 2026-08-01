"""
Unit tests for providers.py.

Tests provider resolution from app config and model listing with a
mocked HTTP layer (no network calls).
"""
import pytest
import requests
from unittest.mock import patch, MagicMock

from chat_rag_explorer.providers import Provider, get_active_provider, list_models


class TestGetActiveProvider:
    """Tests for get_active_provider()."""

    def test_builds_openrouter_from_config(self, app):
        """Provider carries the configured base URL and API key."""
        app.config["OPENROUTER_BASE_URL"] = "https://example.test/v1"
        app.config["OPENROUTER_API_KEY"] = "test-key"

        with app.app_context():
            provider = get_active_provider()

        assert provider.name == "openrouter"
        assert provider.base_url == "https://example.test/v1"
        assert provider.api_key == "test-key"

    def test_missing_api_key_is_none(self, app):
        """Provider api_key is None when unset (app can still start)."""
        app.config["OPENROUTER_API_KEY"] = None

        with app.app_context():
            provider = get_active_provider()

        assert provider.api_key is None


class TestListModels:
    """Tests for list_models() with mocked HTTP."""

    @patch("chat_rag_explorer.providers.requests.get")
    def test_returns_model_data(self, mock_get):
        """Returns the models from OpenRouter's data envelope."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "a/one", "name": "One", "context_length": 8192, "pricing": {}},
                {"id": "b/two", "name": "Two", "context_length": 4096, "pricing": {}},
            ]
        }
        mock_get.return_value = mock_response
        provider = Provider(name="openrouter", base_url="https://example.test/v1", api_key="k")

        models = list_models(provider)

        assert [m["id"] for m in models] == ["a/one", "b/two"]
        mock_get.assert_called_once()
        assert mock_get.call_args.args[0] == "https://example.test/v1/models"

    @patch("chat_rag_explorer.providers.requests.get")
    def test_http_error_propagates(self, mock_get):
        """HTTP failures raise so the route can return a 500."""
        mock_get.side_effect = requests.RequestException("boom")
        provider = Provider(name="openrouter", base_url="https://example.test/v1", api_key="k")

        with pytest.raises(requests.RequestException):
            list_models(provider)

    def test_unknown_provider_raises(self):
        """An unrecognized provider name is a programming error."""
        provider = Provider(name="nonsense", base_url="http://x", api_key=None)

        with pytest.raises(ValueError, match="Unknown provider"):
            list_models(provider)
