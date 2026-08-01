"""
Application configuration loaded from environment variables.

All settings can be customized via a .env file in the project root.
See .env.example for available options and their defaults.

Configuration Groups:
- LLM Provider: provider selection (OpenRouter or Ollama) and connection settings
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

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # Ollama defaults to a local install. For Ollama cloud, point the base
    # URL at https://ollama.com/v1 and set a real API key. A local Ollama
    # has no auth, but the OpenAI SDK requires a non-empty key, so the
    # default is a placeholder that keeps the app configured and working.
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

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
