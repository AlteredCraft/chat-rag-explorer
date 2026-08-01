"""
Application configuration loaded from environment variables.

All settings can be customized via a .env file in the project root.
See .env.example for available options and their defaults.

Configuration Groups:
- LLM Provider: provider selection (LLM_PROVIDER) plus the provider-agnostic
  connection settings LLM_BASE_URL and LLM_API_KEY
- ChromaDB: Vector database connection (local/server/cloud modes)
- Logging: Log levels, outputs, and file paths
- Chat History: Conversation logging settings
- Server: Host, port, and retry behavior
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Which LLM provider serves chat and model listing: "openrouter" or
    # "ollama". Required, with no default on purpose - defaulting would
    # let someone who never made the choice land on OpenRouter and be
    # puzzled by the resulting API key errors. An empty value is reported
    # at startup (main.py) and by get_active_provider(). See providers.py.
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

    # Connection settings for whichever provider LLM_PROVIDER selects.
    # One pair of settings rather than a pair per provider, so switching
    # providers never leaves a stale OPENROUTER_* value shadowing an
    # OLLAMA_* one.
    #
    # Both are left empty here on purpose: the sensible value depends on
    # the provider, so the per-provider fallback lives with the rest of
    # the provider knowledge in providers.PROVIDER_DEFAULTS. Unset means
    # "use the active provider's default", not "no endpoint".
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
    LLM_API_KEY = os.getenv("LLM_API_KEY")

    # Model used when a request specifies none. The frontend fetches this
    # from /api/status, so this is the single source of truth. It must also
    # be listed in .models_list to be selectable in the picker
    # (tests/unit/test_config.py enforces that rule).
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-v4-flash")

    # ChromaDB Configuration
    CHROMADB_API_KEY = os.getenv("CHROMADB_API_KEY")

    # Logging Configuration
    LOG_LEVEL_APP = os.getenv("LOG_LEVEL_APP", "DEBUG")
    LOG_LEVEL_DEPS = os.getenv("LOG_LEVEL_DEPS", "INFO")
    LOG_TO_STDOUT = os.getenv("LOG_TO_STDOUT", "true").lower() == "true"
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/app.log")

    # Chat History Configuration
    CHAT_HISTORY_ENABLED = os.getenv("CHAT_HISTORY_ENABLED", "false").lower() == "true"
    CHAT_HISTORY_PATH = os.getenv("CHAT_HISTORY_PATH", "logs/chat-history.jsonl")

    # Server Configuration
    SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    SERVER_PORT_RETRIES = int(os.getenv("SERVER_PORT_RETRIES", "5"))
