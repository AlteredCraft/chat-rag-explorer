"""
Logging configuration for the application.

Sets up a two-tier logging system:
- App logger (chat_rag_explorer): Detailed DEBUG-level logging for our code
- Root logger: INFO-level logging for third-party dependencies (Flask, requests, etc.)

Supports multiple output targets:
- stdout: For development and container environments
- File: For persistent logs with automatic directory creation
"""
import logging
import os
import sys
from pathlib import Path
from flask import Flask


def setup_logging(app: Flask):
    """
    Configure logging for the application and its dependencies.
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    handlers = []

    # 1. Stdout Handler
    if app.config.get("LOG_TO_STDOUT"):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        handlers.append(stdout_handler)

    # 2. File Handler
    if app.config.get("LOG_TO_FILE"):
        file_path = app.config.get("LOG_FILE_PATH", "logs/app.log")
        # Ensure the logs directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure the Root Logger (for dependencies)
    root_logger = logging.getLogger()
    root_level = getattr(logging, app.config.get("LOG_LEVEL_DEPS", "INFO").upper())
    root_logger.setLevel(root_level)

    # Remove any existing handlers from the root logger
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    for h in handlers:
        root_logger.addHandler(h)

    # Configure the App Logger
    app_logger = logging.getLogger("chat_rag_explorer")
    app_level = getattr(logging, app.config.get("LOG_LEVEL_APP", "DEBUG").upper())
    app_logger.setLevel(app_level)

    # Log only in main process, not reloader child
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        app_logger.debug(
            f"Logging initialized. App level: {app.config.get('LOG_LEVEL_APP')}, Deps level: {app.config.get('LOG_LEVEL_DEPS')}"
        )
