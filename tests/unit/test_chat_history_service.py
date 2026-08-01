"""
Unit tests for chat_history_service.py.

Tests chat history logging with JSONL output.
Uses Flask app context fixture for current_app access.
"""
import json
import pytest
from chat_rag_explorer.chat_history_service import ChatHistoryService, ChatHistoryEntry


def make_entry_data(**overrides):
    """Build a minimal chat entry-data dict, as assembled by the chat route."""
    entry_data = {
        "request_id": "req-123",
        "model": "gpt-4",
        "params": {"temperature": 0.7, "top_p": None},
        "messages": [{"role": "user", "content": "Hello"}],
        "messages_original": [{"role": "user", "content": "Hello"}],
        "response": "Hi there!",
        "status": "success",
        "error": None,
        "tokens": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        "timing": {"total_ms": 1500.0, "ttfc_ms": 300.0},
        "chunks": 10,
        "rag": None,
    }
    entry_data.update(overrides)
    return entry_data


class TestChatHistoryEntry:
    """Tests for ChatHistoryEntry dataclass."""

    def test_to_json_format(self):
        """Entry serializes to compact JSON."""
        entry = ChatHistoryEntry(
            request_id="test-123",
            response_id="resp-456",
            timestamp={"iso": "2025-01-01T12:00:00", "unix": 1735732800},
            request={"messages": [{"role": "user", "content": "Hi"}]},
            response={"content": "Hello!", "status": "success"},
            metrics={"chunks": 5}
        )

        json_str = entry.to_json()
        parsed = json.loads(json_str)

        assert parsed["request_id"] == "test-123"
        assert parsed["response_id"] == "resp-456"
        assert parsed["schema_version"] == "1.1"
        assert parsed["response"]["content"] == "Hello!"

    def test_to_json_no_whitespace(self):
        """JSON output has no extra whitespace (compact)."""
        entry = ChatHistoryEntry(request_id="test")

        json_str = entry.to_json()

        # Compact format: no spaces after colons/commas
        assert ": " not in json_str
        assert ", " not in json_str


class TestChatHistoryService:
    """Tests for ChatHistoryService."""

    def test_is_enabled_default_false(self, app_context):
        """Chat history is disabled by default."""
        service = ChatHistoryService()

        assert service.is_enabled() is False

    def test_is_enabled_false_when_config_key_missing(self, app):
        """Falls back to disabled when CHAT_HISTORY_ENABLED is absent entirely."""
        app.config.pop("CHAT_HISTORY_ENABLED", None)
        service = ChatHistoryService()

        with app.app_context():
            assert service.is_enabled() is False

    def test_is_enabled_respects_config(self, app):
        """is_enabled respects CHAT_HISTORY_ENABLED config."""
        app.config["CHAT_HISTORY_ENABLED"] = False
        service = ChatHistoryService()

        with app.app_context():
            assert service.is_enabled() is False

    def test_log_interaction_writes_file(self, app, tmp_path):
        """log_interaction writes entry to JSONL file."""
        log_file = tmp_path / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = True
        service = ChatHistoryService()

        with app.app_context():
            service.log_interaction(make_entry_data())

        assert log_file.exists()
        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["request_id"] == "req-123"
        assert entry["request"]["llm_params"]["model"] == "gpt-4"
        assert entry["request"]["llm_params"]["temperature"] == 0.7
        assert entry["response"]["content"] == "Hi there!"
        assert entry["metrics"]["chunks"] == 10
        assert entry["metrics"]["timing"]["total_ms"] == 1500.0

    def test_log_interaction_disabled(self, app, tmp_path):
        """No file written when logging is disabled."""
        log_file = tmp_path / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = False
        service = ChatHistoryService()

        with app.app_context():
            service.log_interaction(make_entry_data())

        assert not log_file.exists()

    def test_log_interaction_appends(self, app, tmp_path):
        """Multiple log entries are appended to same file."""
        log_file = tmp_path / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = True
        service = ChatHistoryService()

        with app.app_context():
            for i in range(3):
                service.log_interaction(make_entry_data(request_id=f"req-{i}"))

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["request_id"] == f"req-{i}"

    def test_log_interaction_creates_directory(self, app, tmp_path):
        """Creates parent directory if it doesn't exist."""
        log_file = tmp_path / "subdir" / "deep" / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = True
        service = ChatHistoryService()

        with app.app_context():
            service.log_interaction(make_entry_data())

        assert log_file.exists()

    def test_log_interaction_records_error(self, app, tmp_path):
        """Error status and message are recorded."""
        log_file = tmp_path / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = True
        service = ChatHistoryService()

        with app.app_context():
            service.log_interaction(make_entry_data(
                response="",
                status="error",
                error="Connection timeout",
                tokens=None,
                chunks=0,
            ))

        entry = json.loads(log_file.read_text().strip())
        assert entry["response"]["status"] == "error"
        assert entry["response"]["error"] == "Connection timeout"

    def test_log_interaction_includes_tokens(self, app, tmp_path):
        """Token usage is recorded in metrics."""
        log_file = tmp_path / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = True
        service = ChatHistoryService()

        with app.app_context():
            service.log_interaction(make_entry_data(
                tokens={
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                }
            ))

        entry = json.loads(log_file.read_text().strip())
        assert entry["metrics"]["tokens"]["prompt_tokens"] == 100
        assert entry["metrics"]["tokens"]["completion_tokens"] == 50
        assert entry["metrics"]["tokens"]["total_tokens"] == 150

    def test_log_interaction_records_rag_and_augmented_messages(self, app, tmp_path):
        """RAG metadata and the augmented messages sent to the LLM are recorded."""
        log_file = tmp_path / "history.jsonl"
        app.config["CHAT_HISTORY_PATH"] = str(log_file)
        app.config["CHAT_HISTORY_ENABLED"] = True
        service = ChatHistoryService()

        rag = {
            "enabled": True,
            "documents_retrieved": 1,
            "collection": "my_collection",
            "documents": ["Doc 1"],
        }
        augmented = [{"role": "user", "content": "<knowledge_base_context>...</knowledge_base_context>"}]
        original = [{"role": "user", "content": "What is X?"}]

        with app.app_context():
            service.log_interaction(make_entry_data(
                messages=augmented,
                messages_original=original,
                rag=rag,
            ))

        entry = json.loads(log_file.read_text().strip())
        assert entry["request"]["rag"]["collection"] == "my_collection"
        assert entry["request"]["messages"] == augmented
        assert entry["request"]["messages_original"] == original
