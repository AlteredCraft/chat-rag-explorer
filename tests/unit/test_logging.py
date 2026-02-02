"""
Unit tests for chat_rag_explorer/logging.py.

Tests the decoupled logging setup that can be called early in the application
lifecycle, before Flask is initialized.
"""
import logging
import importlib


class TestSetupLogging:
    """Tests for setup_logging() function."""

    def test_setup_logging_is_idempotent(self, tmp_path, monkeypatch):
        """Calling setup_logging() multiple times should be safe (no-op after first)."""
        # Reset the module state
        import chat_rag_explorer.logging as log_module
        importlib.reload(log_module)

        # Mock config to avoid file operations
        class MockConfig:
            LOG_TO_STDOUT = True
            LOG_TO_FILE = False
            LOG_LEVEL_APP = "DEBUG"
            LOG_LEVEL_DEPS = "INFO"

        # First call should configure logging
        log_module.setup_logging(MockConfig)
        assert log_module._logging_configured is True

        # Count handlers after first setup
        root_logger = logging.getLogger()
        handler_count_after_first = len(root_logger.handlers)

        # Second call should be a no-op
        log_module.setup_logging(MockConfig)
        handler_count_after_second = len(root_logger.handlers)

        # Should not add duplicate handlers
        assert handler_count_after_first == handler_count_after_second

    def test_setup_logging_with_no_args_uses_config(self, monkeypatch):
        """setup_logging() with no args should use Config class."""
        import chat_rag_explorer.logging as log_module
        importlib.reload(log_module)

        # Mock the Config import inside setup_logging
        class MockConfig:
            LOG_TO_STDOUT = True
            LOG_TO_FILE = False
            LOG_LEVEL_APP = "INFO"
            LOG_LEVEL_DEPS = "WARNING"

        monkeypatch.setattr("config.Config", MockConfig)

        # Should not raise, should use Config
        log_module.setup_logging()

        assert log_module._logging_configured is True

    def test_setup_logging_configures_app_logger(self, tmp_path):
        """setup_logging() should configure the chat_rag_explorer logger."""
        import chat_rag_explorer.logging as log_module
        importlib.reload(log_module)

        class MockConfig:
            LOG_TO_STDOUT = True
            LOG_TO_FILE = False
            LOG_LEVEL_APP = "WARNING"
            LOG_LEVEL_DEPS = "ERROR"

        log_module.setup_logging(MockConfig)

        app_logger = logging.getLogger("chat_rag_explorer")
        assert app_logger.level == logging.WARNING

    def test_setup_logging_configures_root_logger(self, tmp_path):
        """setup_logging() should configure the root logger for dependencies."""
        import chat_rag_explorer.logging as log_module
        importlib.reload(log_module)

        class MockConfig:
            LOG_TO_STDOUT = True
            LOG_TO_FILE = False
            LOG_LEVEL_APP = "DEBUG"
            LOG_LEVEL_DEPS = "ERROR"

        log_module.setup_logging(MockConfig)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR

    def test_setup_logging_creates_file_handler(self, tmp_path):
        """setup_logging() should create file handler when LOG_TO_FILE is True."""
        import chat_rag_explorer.logging as log_module
        importlib.reload(log_module)

        log_file = tmp_path / "logs" / "test.log"

        class MockConfig:
            LOG_TO_STDOUT = False
            LOG_TO_FILE = True
            LOG_FILE_PATH = str(log_file)
            LOG_LEVEL_APP = "DEBUG"
            LOG_LEVEL_DEPS = "INFO"

        log_module.setup_logging(MockConfig)

        # Directory should be created
        assert log_file.parent.exists()

        # File handler should be added
        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
