"""
Unit tests for config.py.

Tests environment variable loading and default values.
"""
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


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
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to pick up new env
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.LOG_LEVEL_APP == "DEBUG"

    def test_custom_log_level_app(self):
        """LOG_LEVEL_APP reads from environment."""
        with patch.dict(os.environ, {"LOG_LEVEL_APP": "WARNING"}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.LOG_LEVEL_APP == "WARNING"

    def test_log_to_stdout_default_true(self):
        """LOG_TO_STDOUT defaults to True."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.LOG_TO_STDOUT is True

    def test_log_to_stdout_false(self):
        """LOG_TO_STDOUT parses 'false' string correctly."""
        with patch.dict(os.environ, {"LOG_TO_STDOUT": "false"}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.LOG_TO_STDOUT is False

    def test_server_port_default(self):
        """SERVER_PORT defaults to 8000."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.SERVER_PORT == 8000

    def test_server_port_custom(self):
        """SERVER_PORT reads integer from environment."""
        with patch.dict(os.environ, {"SERVER_PORT": "9000"}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.SERVER_PORT == 9000

    def test_chat_history_enabled_default(self):
        """CHAT_HISTORY_ENABLED defaults to False."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config
            importlib.reload(config)

            assert config.Config.CHAT_HISTORY_ENABLED is False

    def test_openrouter_base_url_default(self):
        """OPENROUTER_BASE_URL defaults to the OpenRouter endpoint."""
        import importlib
        import config
        importlib.reload(config)

        assert config.Config.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"

    def test_openrouter_base_url_env_override(self):
        """Base URL can point at any OpenAI-compatible endpoint (e.g. Ollama)."""
        import importlib
        import config
        try:
            with patch.dict(os.environ, {"OPENROUTER_BASE_URL": "http://localhost:11434/v1"}, clear=True):
                importlib.reload(config)
                assert config.Config.OPENROUTER_BASE_URL == "http://localhost:11434/v1"
        finally:
            # Reload with the real environment so later tests see real values
            importlib.reload(config)

    def test_default_model_env_override(self):
        """DEFAULT_MODEL reads from environment."""
        import importlib
        import config
        try:
            with patch.dict(os.environ, {"DEFAULT_MODEL": "custom/model"}, clear=True):
                importlib.reload(config)
                assert config.Config.DEFAULT_MODEL == "custom/model"
        finally:
            importlib.reload(config)

    def test_llm_provider_defaults_to_openrouter(self):
        """LLM_PROVIDER defaults to openrouter when not set."""
        import importlib
        import config
        try:
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)
                assert config.Config.LLM_PROVIDER == "openrouter"
        finally:
            importlib.reload(config)

    def test_llm_provider_is_normalized(self):
        """LLM_PROVIDER tolerates stray whitespace and capitals."""
        import importlib
        import config
        try:
            with patch.dict(os.environ, {"LLM_PROVIDER": " Ollama "}, clear=True):
                importlib.reload(config)
                assert config.Config.LLM_PROVIDER == "ollama"
        finally:
            importlib.reload(config)

    def test_ollama_defaults_to_local_with_placeholder_key(self):
        """Ollama defaults target a local install and need no real key."""
        import importlib
        import config
        try:
            with patch.dict(os.environ, {}, clear=True):
                importlib.reload(config)
                assert config.Config.OLLAMA_BASE_URL == "http://localhost:11434/v1"
                assert config.Config.OLLAMA_API_KEY == "ollama"
        finally:
            importlib.reload(config)
