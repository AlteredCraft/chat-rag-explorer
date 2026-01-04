"""
Chat RAG Explorer - Flask application factory and initialization.

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

logger = logging.getLogger(__name__)


def is_reloader_process() -> bool:
    """Check if running in Werkzeug reloader child process."""
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from chat_rag_explorer.logging import setup_logging

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
    logger.info("Chat RAG Explorer - Starting up")
    logger.info("=" * 60)

    # Log environment/config (mask sensitive values)
    api_key = app.config.get("OPENROUTER_API_KEY", "")
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if api_key and len(api_key) > 12 else "[NOT SET]"

    logger.info(f"Configuration:")
    logger.info(f"  - OpenRouter Base URL: {app.config.get('OPENROUTER_BASE_URL', 'NOT SET')}")
    logger.info(f"  - OpenRouter API Key: {masked_key}")
    logger.info(f"  - Default Model: {app.config.get('DEFAULT_MODEL', 'NOT SET')}")
    logger.info(f"  - Debug Mode: {app.config.get('DEBUG', False)}")

    logger.info(f"Logging Configuration:")
    logger.info(f"  - App Log Level: {app.config.get('LOG_LEVEL_APP', 'DEBUG')}")
    logger.info(f"  - Deps Log Level: {app.config.get('LOG_LEVEL_DEPS', 'INFO')}")
    logger.info(f"  - Log to Stdout: {app.config.get('LOG_TO_STDOUT', True)}")
    logger.info(f"  - Log to File: {app.config.get('LOG_TO_FILE', True)}")
    if app.config.get('LOG_TO_FILE'):
        logger.info(f"  - Log File Path: {app.config.get('LOG_FILE_PATH', 'app.log')}")

    # Warn about potential issues
    if not api_key:
        logger.warning("OPENROUTER_API_KEY is not set - API calls will fail!")
