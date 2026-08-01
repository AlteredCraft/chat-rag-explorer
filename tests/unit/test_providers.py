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
        app.config["LLM_BASE_URL"] = "https://example.test/v1"
        app.config["LLM_API_KEY"] = "test-key"

        with app.app_context():
            provider = get_active_provider()

        assert provider.name == "openrouter"
        assert provider.base_url == "https://example.test/v1"
        assert provider.api_key == "test-key"

    def test_missing_api_key_is_none(self, app):
        """Provider api_key is None when unset (app can still start)."""
        app.config["LLM_API_KEY"] = None

        with app.app_context():
            provider = get_active_provider()

        assert provider.api_key is None

    def test_builds_ollama_from_config(self, app):
        """LLM_PROVIDER=ollama selects Ollama connection settings."""
        app.config["LLM_PROVIDER"] = "ollama"
        app.config["LLM_BASE_URL"] = "http://localhost:11434/v1"
        app.config["LLM_API_KEY"] = "ollama"

        with app.app_context():
            provider = get_active_provider()

        assert provider.name == "ollama"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.api_key == "ollama"

    def test_ollama_placeholder_key_keeps_app_configured(self, app):
        """The placeholder key is truthy, so is_configured() stays True locally."""
        app.config["LLM_PROVIDER"] = "ollama"
        app.config["LLM_API_KEY"] = "ollama"

        with app.app_context():
            provider = get_active_provider()

        assert bool(provider.api_key) is True


class TestProviderConnectionDefaults:
    """LLM_BASE_URL and LLM_API_KEY fall back per provider, not globally.

    A single shared default is impossible (the providers sit at different
    endpoints), and no default at all would let someone switch
    LLM_PROVIDER to ollama while a stale LLM_BASE_URL still points at
    OpenRouter. Defaulting per provider cannot mismatch.
    """

    def test_openrouter_base_url_defaults_to_openrouter(self, app):
        """Unset LLM_BASE_URL resolves to OpenRouter's endpoint."""
        app.config["LLM_PROVIDER"] = "openrouter"
        app.config["LLM_BASE_URL"] = ""

        with app.app_context():
            provider = get_active_provider()

        assert provider.base_url == "https://openrouter.ai/api/v1"

    def test_ollama_base_url_defaults_to_localhost(self, app):
        """The same unset value resolves to a local Ollama instead."""
        app.config["LLM_PROVIDER"] = "ollama"
        app.config["LLM_BASE_URL"] = ""

        with app.app_context():
            provider = get_active_provider()

        assert provider.base_url == "http://localhost:11434/v1"

    def test_explicit_base_url_overrides_the_default(self, app):
        """Ollama cloud is reached by setting LLM_BASE_URL."""
        app.config["LLM_PROVIDER"] = "ollama"
        app.config["LLM_BASE_URL"] = "https://ollama.com/v1"

        with app.app_context():
            provider = get_active_provider()

        assert provider.base_url == "https://ollama.com/v1"

    def test_ollama_api_key_defaults_to_placeholder(self, app):
        """A local Ollama needs no key, but the OpenAI SDK demands a non-empty one."""
        app.config["LLM_PROVIDER"] = "ollama"
        app.config["LLM_API_KEY"] = None

        with app.app_context():
            provider = get_active_provider()

        assert provider.api_key == "ollama"

    def test_openrouter_api_key_has_no_placeholder(self, app):
        """OpenRouter genuinely needs a key, so unset stays unset."""
        app.config["LLM_PROVIDER"] = "openrouter"
        app.config["LLM_API_KEY"] = None

        with app.app_context():
            provider = get_active_provider()

        assert provider.api_key is None

    def test_explicit_api_key_overrides_the_placeholder(self, app):
        """Ollama cloud's real key wins over the local placeholder."""
        app.config["LLM_PROVIDER"] = "ollama"
        app.config["LLM_API_KEY"] = "real-cloud-key"

        with app.app_context():
            provider = get_active_provider()

        assert provider.api_key == "real-cloud-key"

    def test_unknown_llm_provider_raises(self, app):
        """A typo in LLM_PROVIDER fails loudly with the valid options."""
        app.config["LLM_PROVIDER"] = "nonsense"

        with app.app_context():
            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                get_active_provider()

    def test_unset_llm_provider_raises_rather_than_defaulting(self, app):
        """An unset provider is an error, not a silent fallback to OpenRouter."""
        app.config["LLM_PROVIDER"] = ""

        with app.app_context():
            with pytest.raises(ValueError, match="LLM_PROVIDER is not set"):
                get_active_provider()

    def test_missing_llm_provider_key_raises(self, app):
        """Same when the config key is absent entirely, not just empty."""
        app.config.pop("LLM_PROVIDER", None)

        with app.app_context():
            with pytest.raises(ValueError, match="LLM_PROVIDER is not set"):
                get_active_provider()

    def test_unset_provider_error_names_the_valid_options(self, app):
        """The message tells the user what to set and to what."""
        app.config["LLM_PROVIDER"] = ""

        with app.app_context():
            with pytest.raises(ValueError) as exc_info:
                get_active_provider()

        message = str(exc_info.value)
        assert "openrouter" in message
        assert "ollama" in message


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


class TestListOllamaModels:
    """Tests for list_models() against Ollama's response shape."""

    @patch("chat_rag_explorer.providers.requests.get")
    def test_normalizes_to_frontend_contract(self, mock_get):
        """Ollama entries gain name, context_length, and free pricing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "llama3.2:3b", "object": "model", "owned_by": "library"},
                {"id": "qwen3:8b", "object": "model", "owned_by": "library"},
            ],
        }
        mock_get.return_value = mock_response
        provider = Provider(name="ollama", base_url="http://localhost:11434/v1", api_key="ollama")

        models = list_models(provider)

        assert models == [
            {"id": "llama3.2:3b", "name": "llama3.2:3b", "context_length": None, "pricing": {}},
            {"id": "qwen3:8b", "name": "qwen3:8b", "context_length": None, "pricing": {}},
        ]
        assert mock_get.call_args.args[0] == "http://localhost:11434/v1/models"

    @patch("chat_rag_explorer.providers.requests.get")
    def test_entries_without_id_are_skipped(self, mock_get):
        """A malformed catalog entry doesn't break the whole listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"object": "model"}, {"id": "llama3.2:3b"}]
        }
        mock_get.return_value = mock_response
        provider = Provider(name="ollama", base_url="http://localhost:11434/v1", api_key="ollama")

        models = list_models(provider)

        assert [m["id"] for m in models] == ["llama3.2:3b"]

    @patch("chat_rag_explorer.providers.requests.get")
    def test_connection_error_propagates(self, mock_get):
        """Ollama not running raises so the route can explain the failure."""
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")
        provider = Provider(name="ollama", base_url="http://localhost:11434/v1", api_key="ollama")

        with pytest.raises(requests.exceptions.ConnectionError):
            list_models(provider)
