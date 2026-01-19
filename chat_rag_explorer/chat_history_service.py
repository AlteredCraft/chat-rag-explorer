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
from typing import Any, Dict, List, Optional

from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class ChatHistoryEntry:
    """Represents a single chat history log entry."""

    schema_version: str = "1.0"
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
        """Check if chat history logging is enabled."""
        return current_app.config.get("CHAT_HISTORY_ENABLED", True)

    def log_interaction(
        self,
        request_id: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float],
        top_p: Optional[float],
        response_content: str,
        status: str,
        error: Optional[str],
        total_seconds: float,
        ttfc_seconds: Optional[float],
        chunk_count: int,
        tokens: Optional[Dict[str, int]] = None,
    ) -> None:
        """Log a chat interaction to the history file (thread-safe).

        Args:
            request_id: Unique identifier for the request
            messages: Conversation messages sent to LLM
            model: Model identifier used
            temperature: Sampling temperature (optional)
            top_p: Nucleus sampling parameter (optional)
            response_content: Full accumulated response text
            status: "success" or "error"
            error: Error message if status is "error"
            total_seconds: Total request duration
            ttfc_seconds: Time to first chunk (optional)
            chunk_count: Number of streaming chunks received
            tokens: Token usage dict with prompt_tokens, completion_tokens, total_tokens
        """
        if not self.is_enabled():
            return

        response_id = str(uuid.uuid4())
        now = datetime.now()

        entry = ChatHistoryEntry(
            schema_version="1.0",
            request_id=request_id,
            response_id=response_id,
            timestamp={"iso": now.isoformat(), "unix": now.timestamp()},
            request={
                "messages": messages,
                "llm_params": {
                    "model": model,
                    "temperature": temperature,
                    "top_p": top_p,
                },
            },
            response={
                "content": response_content,
                "status": status,
                "error": error,
            },
            metrics={
                "timing": {
                    "total_seconds": round(total_seconds, 3),
                    "ttfc_seconds": round(ttfc_seconds, 3) if ttfc_seconds else None,
                },
                "tokens": tokens,
                "chunks": chunk_count,
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
