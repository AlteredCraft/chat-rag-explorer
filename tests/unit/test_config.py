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
    for line in models_list.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            ids.append(stripped)
    return ids


def read_frontend_default_model(js_filename):
    """
    Extract the DEFAULT_MODEL constant from a frontend JavaScript file.

    Args:
        js_filename: Name of the file in chat_rag_explorer/static/

    Returns:
        The model ID string, or None if the constant was not found
    """
    js_path = PROJECT_ROOT / "chat_rag_explorer" / "static" / js_filename
    match = re.search(
        r"""const DEFAULT_MODEL = ['"]([^'"]+)['"]""", js_path.read_text()
    )
    return match.group(1) if match else None


class TestDefaultModelConsistency:
    """
    The default model must agree across config.py, the frontend, and .models_list.

    These three drifted apart once already: config.py was updated while both
    frontend files kept a stale model ID that was no longer in .models_list. The
    browser sends a model on every chat request, so the frontend constant is what
    a first-time user actually gets - the backend default never fires for them.
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

    @pytest.mark.parametrize("js_filename", ["script.js", "settings.js"])
    def test_frontend_default_matches_backend(self, js_filename):
        """Each frontend DEFAULT_MODEL must match the one in config.py."""
        from config import Config

        frontend_default = read_frontend_default_model(js_filename)

        assert frontend_default == Config.DEFAULT_MODEL, (
            f"{js_filename} defaults to {frontend_default!r} but config.py uses "
            f"{Config.DEFAULT_MODEL!r}"
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

    def test_openrouter_base_url_constant(self):
        """OPENROUTER_BASE_URL is hardcoded constant."""
        import importlib
        import config
        importlib.reload(config)

        assert config.Config.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
