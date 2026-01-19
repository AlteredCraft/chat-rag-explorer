"""
Application entry point for Chat RAG Explorer.

This module handles:
- Flask application startup with debug mode
- Automatic port discovery (tries ports 8000-8004 if one is busy)
- Werkzeug reloader compatibility for hot-reloading during development
- Environment validation (requires .env with OPENROUTER_API_KEY)

Usage:
    uv run main.py
"""
import logging
import os
import socket
import sys
from pathlib import Path

from chat_rag_explorer import create_app, is_reloader_process
from config import Config

logger = logging.getLogger("chat_rag_explorer")


def validate_environment() -> None:
    """
    Validate required environment configuration exists.

    Checks:
    - .env file exists in project root
    - OPENROUTER_API_KEY is set and not empty

    Exits with helpful error message if validation fails.
    """
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("\n❌ ERROR: .env file not found!", file=sys.stderr)
        print("\nTo get started:", file=sys.stderr)
        print("  1. Copy .env.example to .env:", file=sys.stderr)
        print("     cp .env.example .env", file=sys.stderr)
        print("  2. Add your OpenRouter API key to .env:", file=sys.stderr)
        print("     OPENROUTER_API_KEY=your_api_key_here", file=sys.stderr)
        print("\nGet an API key at: https://openrouter.ai/keys\n", file=sys.stderr)
        sys.exit(1)

    if not Config.OPENROUTER_API_KEY:
        print("\n❌ ERROR: OPENROUTER_API_KEY is not set!", file=sys.stderr)
        print("\nAdd your OpenRouter API key to .env:", file=sys.stderr)
        print("  OPENROUTER_API_KEY=your_api_key_here", file=sys.stderr)
        print("\nGet an API key at: https://openrouter.ai/keys\n", file=sys.stderr)
        sys.exit(1)


validate_environment()
app = create_app()


def is_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(host: str, base_port: int, max_attempts: int) -> int | None:
    """Find an available port, logging warnings for ports in use."""
    for attempt in range(max_attempts):
        port = base_port + attempt
        if is_port_available(host, port):
            return port
        logger.warning(f"Port {port} is in use, trying next...")
    return None


if __name__ == "__main__":
    host = Config.SERVER_HOST
    base_port = Config.SERVER_PORT
    max_attempts = Config.SERVER_PORT_RETRIES

    if not is_reloader_process():
        port = find_available_port(host, base_port, max_attempts)
        if port is None:
            logger.error(
                f"No available port in range {base_port}-{base_port + max_attempts - 1}"
            )
            exit(1)
        os.environ["_FLASK_PORT"] = str(port)
        logger.info(f"🚀 Running on: {host}:{port}")
        logger.info("=" * 60)
    else:
        port = int(os.environ.get("_FLASK_PORT", base_port))

    app.run(debug=True, host=host, port=port)
