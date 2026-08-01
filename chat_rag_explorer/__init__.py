"""
RAG Lab - Flask application factory and initialization.

This module provides:
- create_app(): Factory function that creates and configures the Flask app
- is_reloader_process(): Helper to detect Werkzeug's reloader child process

The application factory pattern allows for easy testing and multiple
app instances with different configurations.
"""
import logging
import os
from flask import Flask
from config import Config

from chat_rag_explorer.utils import mask_api_key

logger = logging.getLogger(__name__)


def is_reloader_process() -> bool:
    """Check if running in Werkzeug reloader child process."""
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from chat_rag_explorer.logging import setup_logging

    # setup_logging() is idempotent - safe to call even if already configured in main.py
    setup_logging(app)

    # Log startup configuration only in main process (not reloader child)
    if not is_reloader_process():
        _log_startup_config(app)

    from chat_rag_explorer.routes import main_bp

    app.register_blueprint(main_bp)

    if not is_reloader_process():
        logger.info("Application startup complete - ready to serve requests")

    return app


def _log_startup_config(app):
    """Log important configuration values at startup."""
    logger.info("=" * 60)
    logger.info("RAG Lab - Starting up")
    logger.info("=" * 60)

    # Log environment/config (mask sensitive values). LLM_PROVIDER has no
    # default, so an unset value is reported as such rather than shown as
    # whichever provider's settings we happened to read.
    provider_name = app.config.get("LLM_PROVIDER")
    if provider_name == "ollama":
        base_url = app.config.get("OLLAMA_BASE_URL", "NOT SET")
        api_key = app.config.get("OLLAMA_API_KEY", "")
        key_env_var = "OLLAMA_API_KEY"
    elif provider_name == "openrouter":
        base_url = app.config.get("OPENROUTER_BASE_URL", "NOT SET")
        api_key = app.config.get("OPENROUTER_API_KEY", "")
        key_env_var = "OPENROUTER_API_KEY"
    else:
        base_url = "NOT SET"
        api_key = ""
        # No provider resolved, so no API key setting to point at - the
        # provider selection itself is what needs fixing.
        key_env_var = None

    logger.info("Configuration:")
    logger.info(f"  - LLM Provider: {provider_name or 'NOT SET'}")
    logger.info(f"  - Base URL: {base_url}")
    logger.info(f"  - API Key: {mask_api_key(api_key)}")
    logger.info(f"  - Default Model: {app.config.get('DEFAULT_MODEL', 'NOT SET')}")
    logger.info(f"  - Debug Mode: {app.config.get('DEBUG', False)}")

    logger.info("Logging Configuration:")
    logger.info(f"  - App Log Level: {app.config.get('LOG_LEVEL_APP', 'DEBUG')}")
    logger.info(f"  - Deps Log Level: {app.config.get('LOG_LEVEL_DEPS', 'INFO')}")
    logger.info(f"  - Log to Stdout: {app.config.get('LOG_TO_STDOUT', True)}")
    logger.info(f"  - Log to File: {app.config.get('LOG_TO_FILE', True)}")
    if app.config.get('LOG_TO_FILE'):
        logger.info(f"  - Log File Path: {app.config.get('LOG_FILE_PATH', 'app.log')}")

    # Warn about potential issues
    if key_env_var is None:
        problem = "is not set" if not provider_name else f"is not supported: '{provider_name}'"
        logger.warning(f"LLM_PROVIDER {problem} - API calls will fail!")
    elif not api_key:
        logger.warning(f"{key_env_var} is not set - API calls will fail!")
