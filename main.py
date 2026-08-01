"""
Application entry point for RAG Lab.

This module handles:
- Flask application startup with debug mode
- Automatic port discovery (tries ports 8000-8004 if one is busy)
- Werkzeug reloader compatibility for hot-reloading during development
- Environment validation (warns if .env or OPENROUTER_API_KEY missing, but allows startup)
- Sample database setup (copies pristine sample to working directory on first run)

The app will start without an API key configured. In this case:
- Console shows warning messages with setup instructions
- Frontend displays a prominent banner explaining the situation
- Chat input is disabled until an API key is configured

Usage:
    uv run main.py
"""
import logging
import os
import shutil
import socket
from pathlib import Path

from chat_rag_explorer import create_app, is_reloader_process
from chat_rag_explorer.logging import setup_logging
from chat_rag_explorer.providers import SUPPORTED_PROVIDERS
from config import Config

# Configure logging early so all startup functions can log properly
setup_logging()

logger = logging.getLogger("chat_rag_explorer")


def validate_environment() -> None:
    """
    Validate required environment configuration exists.

    Checks:
    - LLM_PROVIDER is set and names a supported provider (it is required
      and has no default, so "unset" is its own reported failure)
    - .env file exists in project root
    - LLM_API_KEY is set when OpenRouter is the active provider
      (a local Ollama needs no key, so it is not checked)
    - no renamed-away settings are left in .env, which would otherwise
      look configured while being ignored

    Logs warnings if validation fails but allows the app to start.
    The frontend will display appropriate messaging when API key is missing.
    """
    if not Config.LLM_PROVIDER:
        logger.warning("=" * 60)
        logger.warning("LLM_PROVIDER is not set!")
        logger.warning(f"Add it to .env as one of: {', '.join(SUPPORTED_PROVIDERS)}")
        logger.warning("  LLM_PROVIDER=openrouter")
        logger.warning("API calls will fail until this is fixed.")
        logger.warning("=" * 60)
    elif Config.LLM_PROVIDER not in SUPPORTED_PROVIDERS:
        logger.warning("=" * 60)
        logger.warning(f"LLM_PROVIDER is set to '{Config.LLM_PROVIDER}', which is not supported!")
        logger.warning(f"Set LLM_PROVIDER in .env to one of: {', '.join(SUPPORTED_PROVIDERS)}")
        logger.warning("API calls will fail until this is fixed.")
        logger.warning("=" * 60)

    # Checked before the .env-missing branch below returns: the renamed
    # settings can also be exported in the shell, so this is worth saying
    # whether or not a .env exists.
    _warn_about_renamed_settings()

    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        logger.warning("=" * 60)
        logger.warning(".env file not found!")
        logger.warning("To get started:")
        logger.warning("  1. Copy .env.example to .env:")
        logger.warning("     cp .env.example .env")
        logger.warning("  2. Add your OpenRouter API key to .env:")
        logger.warning("     LLM_API_KEY=your_api_key_here")
        logger.warning("Get an API key at: https://openrouter.ai/keys")
        logger.warning("(Or run models locally: set LLM_PROVIDER=ollama - see README)")
        logger.warning("=" * 60)
        return

    if Config.LLM_PROVIDER == "openrouter" and not Config.LLM_API_KEY:
        logger.warning("=" * 60)
        logger.warning("LLM_API_KEY is not set!")
        logger.warning("Add your OpenRouter API key to .env:")
        logger.warning("  LLM_API_KEY=your_api_key_here")
        logger.warning("Get an API key at: https://openrouter.ai/keys")
        logger.warning("=" * 60)


# Settings that were collapsed into LLM_BASE_URL / LLM_API_KEY, mapped to
# their replacement. An .env (or shell) carried over from an earlier
# version still has these, and they are now ignored - which looks exactly
# like the app losing your key unless we say so.
RENAMED_SETTINGS = {
    "OPENROUTER_API_KEY": "LLM_API_KEY",
    "OLLAMA_API_KEY": "LLM_API_KEY",
    "OPENROUTER_BASE_URL": "LLM_BASE_URL",
    "OLLAMA_BASE_URL": "LLM_BASE_URL",
}


def _warn_about_renamed_settings() -> None:
    """Warn when a variable that was renamed away is still set."""
    stale = [name for name in RENAMED_SETTINGS if os.getenv(name)]
    if not stale:
        return

    logger.warning("=" * 60)
    logger.warning("Found settings that are no longer used:")
    for name in stale:
        logger.warning(f"  {name} -> renamed to {RENAMED_SETTINGS[name]}")
    logger.warning("These are ignored. Rename them so your settings take effect.")
    logger.warning("=" * 60)


def setup_sample_database() -> None:
    """
    Copy the sample ChromaDB database to the working directory on first run.

    The repository includes a pristine sample database at data/chroma_db_sample/
    which gets copied to data/chroma_db/ (gitignored) to prevent git deltas
    from ChromaDB's internal file mutations during read operations.

    This function:
    - Creates data/chroma_db/ if it doesn't exist
    - Copies the sample database only if the destination doesn't already exist
    - Provides helpful terminal output about the setup process
    """
    project_root = Path(__file__).parent
    sample_dir = project_root / "data" / "chroma_db_sample"
    working_dir = project_root / "data" / "chroma_db"

    # Check if sample exists
    if not sample_dir.exists():
        logger.debug("No sample database found at data/chroma_db_sample/")
        return

    # Get the sample database name (subdirectory containing the actual DB)
    sample_dbs = [d for d in sample_dir.iterdir() if d.is_dir()]
    sample_sqlite = sample_dir / "chroma.sqlite3"

    if not sample_sqlite.exists():
        logger.debug("Sample directory exists but contains no ChromaDB database")
        return

    # Create working directory if needed
    if not working_dir.exists():
        working_dir.mkdir(parents=True)
        logger.info("📁 Created data/chroma_db/ directory for working databases")

    # Check if sample has already been copied (look for the sqlite file)
    dest_sqlite = working_dir / "chroma.sqlite3"
    if dest_sqlite.exists():
        logger.info("✓ Sample database already present in data/chroma_db/")
        return

    # Copy the sample database
    logger.info("=" * 60)
    logger.info("📦 Setting up sample ChromaDB database...")
    logger.info(f"   Source: data/chroma_db_sample/")
    logger.info(f"   Destination: data/chroma_db/")

    try:
        # Copy the sqlite file
        shutil.copy2(sample_sqlite, dest_sqlite)
        logger.info("   ✓ Copied chroma.sqlite3")

        # Copy any subdirectories (collection data)
        for subdir in sample_dbs:
            dest_subdir = working_dir / subdir.name
            if not dest_subdir.exists():
                shutil.copytree(subdir, dest_subdir)
                logger.info(f"   ✓ Copied collection data: {subdir.name}")

        logger.info("✅ Sample database ready!")
        logger.info("   Use 'data/chroma_db' in RAG Settings to access it.")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Failed to copy sample database: {e}")
        logger.error("   You can manually copy data/chroma_db_sample/ to data/chroma_db/")


validate_environment()
app = create_app()
setup_sample_database()


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
