"""
Chat history logging service for recording LLM interactions.

This module demonstrates how to persist chat conversations for later analysis.
Each interaction is logged as a single JSON line (JSONL format), making it easy
to process logs with standard Unix tools or load into analytics systems.

Key Concepts:
- JSONL Format: One complete JSON object per line, ideal for append-only logs
- Thread Safety: Uses threading.Lock to safely write from concurrent requests
- Dataclasses: Structured data with automatic serialization via asdict()
- Schema Versioning: Each entry includes schema_version for future compatibility

The logged data is useful for:
- Debugging conversation flow and model responses
- Analyzing token usage and response times
- Training data collection (with user consent)
- Audit trails for compliance requirements
"""

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class ChatHistoryEntry:
    """Represents a single chat history log entry.

    Schema versions:
    - 1.0: original format (timing in seconds, original messages only)
    - 1.1: request gains messages_original and rag; timing recorded in
      milliseconds, matching the metadata payload sent to the client
    """

    schema_version: str = "1.1"
    request_id: str = ""
    response_id: str = ""
    timestamp: Dict[str, Any] = field(default_factory=dict)
    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string for JSONL output."""
        return json.dumps(asdict(self), separators=(",", ":"))


class ChatHistoryService:
    """Thread-safe service for logging chat interactions to JSONL."""

    def __init__(self):
        self._lock = threading.Lock()
        self._log_path: Optional[Path] = None

    def _get_log_path(self) -> Path:
        """Get the chat history log file path, creating directory if needed."""
        if self._log_path is None:
            # Default: logs/chat-history.jsonl in project root
            file_path = current_app.config.get(
                "CHAT_HISTORY_PATH", "logs/chat-history.jsonl"
            )
            base_path = Path(file_path)

            # Ensure directory exists
            base_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_path = base_path

        return self._log_path

    def is_enabled(self) -> bool:
        """Check if chat history logging is enabled.

        Defaults to False when unset, matching the Config default.
        """
        return current_app.config.get("CHAT_HISTORY_ENABLED", False)

    def log_interaction(self, entry_data: Dict[str, Any]) -> None:
        """Log a chat interaction to the history file (thread-safe).

        Takes the same entry-data dict the chat route sends to the client as
        its final metadata payload, so the history log and the client details
        modal always agree.

        Args:
            entry_data: Dict with request_id, model, params, messages (as sent
                to the LLM), messages_original, response, status, error,
                tokens, timing ({total_ms, ttfc_ms}), chunks, and rag
        """
        if not self.is_enabled():
            return

        now = datetime.now()
        response_content = entry_data.get("response", "")

        entry = ChatHistoryEntry(
            request_id=entry_data.get("request_id", ""),
            response_id=str(uuid.uuid4()),
            timestamp={"iso": now.isoformat(), "unix": now.timestamp()},
            request={
                "messages": entry_data.get("messages", []),
                "messages_original": entry_data.get("messages_original", []),
                "llm_params": {
                    "model": entry_data.get("model"),
                    **entry_data.get("params", {}),
                },
                "rag": entry_data.get("rag"),
            },
            response={
                "content": response_content,
                "status": entry_data.get("status"),
                "error": entry_data.get("error"),
            },
            metrics={
                "timing": entry_data.get("timing", {}),
                "tokens": entry_data.get("tokens"),
                "chunks": entry_data.get("chunks"),
                "content_length": len(response_content),
            },
        )

        self._write_entry(entry)

    def _write_entry(self, entry: ChatHistoryEntry) -> None:
        """Write entry to log file with thread-safe locking."""
        try:
            log_path = self._get_log_path()

            with self._lock:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(entry.to_json() + "\n")

            logger.debug(f"Logged chat interaction: {entry.request_id}")

        except Exception as e:
            logger.error(f"Failed to write chat history: {e}")


# Singleton instance
chat_history_service = ChatHistoryService()
