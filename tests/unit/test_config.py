"""
Unit tests for config.py.

Tests environment variable loading and default values.
"""
import importlib
import os
import re
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


@contextmanager
def reloaded_config(env=None):
    """Reload config.py with `env` as the entire environment.

    config.py calls load_dotenv() at import, which reads the real .env
    from disk. Reloading without neutralizing that would refill the
    environment these tests just cleared, making assertions about
    defaults depend on whatever the developer happens to have in .env -
    and pass in CI only because CI has no .env at all. Patching it out
    means these tests check config.py's defaults, not the machine's.

    Always reloads once more on the way out so later tests see the real
    configuration.
    """
    import config

    try:
        with patch.dict(os.environ, env or {}, clear=True), patch("dotenv.load_dotenv"):
            importlib.reload(config)
            yield config
    finally:
        importlib.reload(config)


def read_models_list_ids():
    """
    Read model IDs from .models_list, skipping comments and blank lines.

    Returns:
        List of model ID strings, or None if the file does not exist
        (which means no filter is applied and all models are available)
    """
    models_list = PROJECT_ROOT / ".models_list"
    if not models_list.exists():
        return None

    ids = []
    for line in models_list.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            ids.append(stripped)
    return ids


class TestDefaultModelConsistency:
    """
    The default model must be selectable in the model picker.

    The frontend fetches the default from /api/status (single source of
    truth in config.py), so the only rule left to enforce is that the
    default appears in .models_list when that filter file exists.
    """

    def test_default_model_is_in_models_list(self):
        """DEFAULT_MODEL must be selectable, so it has to be in .models_list."""
        from config import Config

        model_ids = read_models_list_ids()
        if model_ids is None:
            pytest.skip("No .models_list file, so no filtering is applied")

        assert Config.DEFAULT_MODEL in model_ids, (
            f"DEFAULT_MODEL is {Config.DEFAULT_MODEL!r}, which is missing from "
            f".models_list, so it will not appear in the model picker"
        )

    def test_frontend_has_no_hardcoded_default_model(self):
        """The frontend must fetch the default from /api/status, not hardcode it.

        The old hardcoded constants drifted from config.py once already;
        this guards against the pattern being reintroduced.
        """
        for js_filename in ["script.js", "settings.js"]:
            js_path = PROJECT_ROOT / "chat_rag_explorer" / "static" / js_filename
            # UTF-8 explicitly: Windows' locale default (cp1252) cannot decode
            # the non-ASCII characters these files contain.
            content = js_path.read_text(encoding="utf-8")
            assert not re.search(r"const DEFAULT_MODEL\s*=", content), (
                f"{js_filename} hardcodes DEFAULT_MODEL; it must use the "
                f"default_model value served by /api/status instead"
            )


class TestConfig:
    """Tests for Config class environment variable loading."""

    def test_default_log_level_app(self):
        """LOG_LEVEL_APP defaults to DEBUG when not set."""
        with reloaded_config({}) as config:
            assert config.Config.LOG_LEVEL_APP == "DEBUG"

    def test_custom_log_level_app(self):
        """LOG_LEVEL_APP reads from environment."""
        with reloaded_config({"LOG_LEVEL_APP": "WARNING"}) as config:
            assert config.Config.LOG_LEVEL_APP == "WARNING"

    def test_log_to_stdout_default_true(self):
        """LOG_TO_STDOUT defaults to True."""
        with reloaded_config({}) as config:
            assert config.Config.LOG_TO_STDOUT is True

    def test_log_to_stdout_false(self):
        """LOG_TO_STDOUT parses 'false' string correctly."""
        with reloaded_config({"LOG_TO_STDOUT": "false"}) as config:
            assert config.Config.LOG_TO_STDOUT is False

    def test_server_port_default(self):
        """SERVER_PORT defaults to 8000."""
        with reloaded_config({}) as config:
            assert config.Config.SERVER_PORT == 8000

    def test_server_port_custom(self):
        """SERVER_PORT reads integer from environment."""
        with reloaded_config({"SERVER_PORT": "9000"}) as config:
            assert config.Config.SERVER_PORT == 9000

    def test_chat_history_enabled_default(self):
        """CHAT_HISTORY_ENABLED defaults to False."""
        with reloaded_config({}) as config:
            assert config.Config.CHAT_HISTORY_ENABLED is False

    def test_llm_base_url_is_empty_when_unset(self):
        """Config holds no endpoint default; providers.py supplies one per provider."""
        with reloaded_config({}) as config:
            assert config.Config.LLM_BASE_URL == ""

    def test_llm_base_url_env_override(self):
        """Base URL can point at any OpenAI-compatible endpoint."""
        with reloaded_config({"LLM_BASE_URL": "http://localhost:11434/v1"}) as config:
            assert config.Config.LLM_BASE_URL == "http://localhost:11434/v1"

    def test_default_model_env_override(self):
        """DEFAULT_MODEL reads from environment."""
        with reloaded_config({"DEFAULT_MODEL": "custom/model"}) as config:
            assert config.Config.DEFAULT_MODEL == "custom/model"

    def test_llm_provider_has_no_default(self):
        """LLM_PROVIDER is required: unset resolves to empty, never a silent default.

        A default here would let a user who never set LLM_PROVIDER end up
        talking to OpenRouter without having chosen it. Startup validation
        reports the empty value instead.
        """
        with reloaded_config({}) as config:
            assert config.Config.LLM_PROVIDER == ""

    def test_llm_provider_is_normalized(self):
        """LLM_PROVIDER tolerates stray whitespace and capitals."""
        with reloaded_config({"LLM_PROVIDER": " Ollama "}) as config:
            assert config.Config.LLM_PROVIDER == "ollama"

    def test_llm_api_key_has_no_default(self):
        """No placeholder in config; the per-provider fallback lives in providers.py."""
        with reloaded_config({}) as config:
            assert config.Config.LLM_API_KEY is None

    def test_legacy_provider_specific_settings_are_gone(self):
        """The per-provider variables were collapsed into LLM_BASE_URL/LLM_API_KEY.

        Guards against a partial revert leaving a second source of truth
        that silently shadows the unified setting.
        """
        with reloaded_config() as config:
            for legacy in (
                "OPENROUTER_API_KEY",
                "OPENROUTER_BASE_URL",
                "OLLAMA_API_KEY",
                "OLLAMA_BASE_URL",
            ):
                assert not hasattr(config.Config, legacy)
