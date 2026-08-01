"""
Unit tests for the application factory's startup banner.

The banner is the first thing a user sees when the app misbehaves, so
the provider state it reports has to be accurate: LLM_PROVIDER is
required and has no default, and "unset" and "misspelled" are different
problems with different fixes.
"""
import logging

from chat_rag_explorer import _log_startup_config


class TestStartupConfigWarnings:
    """Tests for the misconfiguration warnings in _log_startup_config()."""

    def test_reports_unset_provider(self, app, caplog):
        """An unset LLM_PROVIDER is named as the problem, not a missing key."""
        app.config["LLM_PROVIDER"] = ""

        with caplog.at_level(logging.WARNING, logger="chat_rag_explorer"):
            _log_startup_config(app)

        assert "LLM_PROVIDER is not set" in caplog.text

    def test_reports_unsupported_provider_as_unsupported(self, app, caplog):
        """A typo is reported as unsupported, not as 'not set'."""
        app.config["LLM_PROVIDER"] = "openroutr"

        with caplog.at_level(logging.WARNING, logger="chat_rag_explorer"):
            _log_startup_config(app)

        assert "not supported" in caplog.text
        assert "openroutr" in caplog.text
        assert "is not set" not in caplog.text

    def test_reports_missing_api_key_for_resolved_provider(self, app, caplog):
        """With a valid provider, the warning points at that provider's key."""
        app.config["LLM_PROVIDER"] = "openrouter"
        app.config["LLM_API_KEY"] = ""

        with caplog.at_level(logging.WARNING, logger="chat_rag_explorer"):
            _log_startup_config(app)

        assert "LLM_API_KEY is not set" in caplog.text

    def test_silent_when_fully_configured(self, app, caplog):
        """A correctly configured app logs no misconfiguration warning."""
        app.config["LLM_PROVIDER"] = "openrouter"
        app.config["LLM_API_KEY"] = "sk-or-v1-key"

        with caplog.at_level(logging.WARNING, logger="chat_rag_explorer"):
            _log_startup_config(app)

        assert "will fail" not in caplog.text
