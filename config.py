"""
Application configuration loaded from environment variables.

All settings can be customized via a .env file in the project root.
See .env.example for available options and their defaults.

Configuration Groups:
- OpenRouter API: LLM provider settings
- ChromaDB: Vector database connection (local/server/cloud modes)
- Logging: Log levels, outputs, and file paths
- Chat History: Conversation logging settings
- Server: Host, port, and retry behavior
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    # Any OpenAI-compatible endpoint works here (e.g. a local Ollama at
    # http://localhost:11434/v1); OpenRouter is the default.
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

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
