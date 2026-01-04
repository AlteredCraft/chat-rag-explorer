"""
Unit tests for config.py.

Tests environment variable loading and default values.
"""
import os
from unittest.mock import patch


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
