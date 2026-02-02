"""
Logging configuration for the application.

Sets up a two-tier logging system:
- App logger (chat_rag_explorer): Detailed DEBUG-level logging for our code
- Root logger: INFO-level logging for third-party dependencies (Flask, requests, etc.)

Supports multiple output targets:
- stdout: For development and container environments
- File: For persistent logs with automatic directory creation

The setup_logging() function is decoupled from Flask and can be called early
in the application lifecycle (before create_app()) using the Config class directly.
"""
import logging
import os
import sys
from pathlib import Path

# Track if logging has been configured to make setup_logging() idempotent
_logging_configured = False


def setup_logging(config=None):
    """
    Configure logging for the application and its dependencies.

    Can be called with:
    - No arguments: Uses Config class directly (for early startup)
    - Flask app: Uses app.config (for backwards compatibility)
    - Config class: Uses class attributes directly

    This function is idempotent - calling it multiple times is safe.
    The first call configures logging; subsequent calls are no-ops.

    Args:
        config: Optional. A Flask app, Config class, or None (uses Config).
    """
    global _logging_configured

    if _logging_configured:
        return

    # Resolve config source
    if config is None:
        from config import Config
        config = Config
    elif hasattr(config, 'config'):
        # Flask app passed - extract its config
        config = config.config

    # Helper to get config values (works with dict-like or class attributes)
    def get_config(key, default=None):
        if hasattr(config, 'get'):
            return config.get(key, default)
        return getattr(config, key, default)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    handlers = []

    # 1. Stdout Handler
    if get_config("LOG_TO_STDOUT", True):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        handlers.append(stdout_handler)

    # 2. File Handler
    if get_config("LOG_TO_FILE", True):
        file_path = get_config("LOG_FILE_PATH", "logs/app.log")
        # Ensure the logs directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure the Root Logger (for dependencies)
    root_logger = logging.getLogger()
    root_level = getattr(logging, get_config("LOG_LEVEL_DEPS", "INFO").upper())
    root_logger.setLevel(root_level)

    # Remove any existing handlers from the root logger
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    for h in handlers:
        root_logger.addHandler(h)

    # Configure the App Logger
    app_logger = logging.getLogger("chat_rag_explorer")
    app_level = getattr(logging, get_config("LOG_LEVEL_APP", "DEBUG").upper())
    app_logger.setLevel(app_level)

    _logging_configured = True

    # Log only in main process, not reloader child
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        app_logger.debug(
            f"Logging initialized. App level: {get_config('LOG_LEVEL_APP')}, "
            f"Deps level: {get_config('LOG_LEVEL_DEPS')}"
        )
