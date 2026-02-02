"""
Unit tests for services.py pure helper functions.

Tests the extracted pure functions that don't require mocking.
"""
import json
import pytest
from unittest.mock import patch
from chat_rag_explorer.services import (
    mask_api_key,
    build_chat_params,
    extract_usage_data,
    format_metadata_marker,
    sort_models_by_name,
    get_models_list_status,
)


class TestMaskApiKey:
    """Tests for mask_api_key function."""

    def test_masks_long_key(self):
        """Long API keys show first 8 and last 4 chars."""
        key = "sk-1234567890abcdefghij"
        assert mask_api_key(key) == "sk-12345...ghij"

    def test_masks_exactly_13_chars(self):
        """Keys with exactly 13 chars are masked."""
        key = "1234567890123"
        assert mask_api_key(key) == "12345678...0123"

    def test_short_key_returns_missing(self):
        """Keys with 12 or fewer chars return [MISSING]."""
        assert mask_api_key("123456789012") == "[MISSING]"
        assert mask_api_key("short") == "[MISSING]"

    def test_empty_string_returns_missing(self):
        """Empty string returns [MISSING]."""
        assert mask_api_key("") == "[MISSING]"

    def test_none_returns_missing(self):
        """None returns [MISSING]."""
        assert mask_api_key(None) == "[MISSING]"


class TestBuildChatParams:
    """Tests for build_chat_params function."""

    def test_basic_params(self):
        """Builds params with required fields."""
        messages = [{"role": "user", "content": "Hello"}]
        params = build_chat_params("gpt-4", messages)

        assert params["model"] == "gpt-4"
        assert params["messages"] == messages
        assert params["stream"] is True
        assert params["stream_options"] == {"include_usage": True}

    def test_excludes_none_temperature(self):
        """Temperature is excluded when None."""
        params = build_chat_params("gpt-4", [], temperature=None)
        assert "temperature" not in params

    def test_includes_temperature_when_set(self):
        """Temperature is included when provided."""
        params = build_chat_params("gpt-4", [], temperature=0.7)
        assert params["temperature"] == 0.7

    def test_includes_zero_temperature(self):
        """Temperature of 0 is included (not treated as falsy)."""
        params = build_chat_params("gpt-4", [], temperature=0)
        assert params["temperature"] == 0

    def test_excludes_none_top_p(self):
        """top_p is excluded when None."""
        params = build_chat_params("gpt-4", [], top_p=None)
        assert "top_p" not in params

    def test_includes_top_p_when_set(self):
        """top_p is included when provided."""
        params = build_chat_params("gpt-4", [], top_p=0.9)
        assert params["top_p"] == 0.9

    def test_includes_both_optional_params(self):
        """Both temperature and top_p included when set."""
        params = build_chat_params("gpt-4", [], temperature=0.5, top_p=0.8)
        assert params["temperature"] == 0.5
        assert params["top_p"] == 0.8


class TestExtractUsageData:
    """Tests for extract_usage_data function."""

    def test_extracts_usage_from_chunk(self):
        """Extracts token counts from chunk with usage."""
        chunk = _make_chunk(usage=_make_usage(10, 20, 30), model="gpt-4")

        result = extract_usage_data(chunk, "fallback-model")

        assert result == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "model": "gpt-4",
        }

    def test_uses_fallback_model_when_chunk_model_is_none(self):
        """Uses fallback model when chunk.model is None."""
        chunk = _make_chunk(usage=_make_usage(1, 2, 3), model=None)

        result = extract_usage_data(chunk, "fallback-model")

        assert result["model"] == "fallback-model"

    def test_returns_none_when_no_usage(self):
        """Returns None when chunk has no usage attribute."""
        chunk = _make_chunk(usage=None)

        result = extract_usage_data(chunk, "fallback")

        assert result is None

    def test_returns_none_when_usage_attr_missing(self):
        """Returns None when chunk lacks usage attribute entirely."""
        chunk = object()  # No usage attribute

        result = extract_usage_data(chunk, "fallback")

        assert result is None


class TestFormatMetadataMarker:
    """Tests for format_metadata_marker function."""

    def test_formats_as_prefixed_json(self):
        """Formats usage data as __METADATA__:{json}."""
        usage = {"prompt_tokens": 10, "total_tokens": 15}

        result = format_metadata_marker(usage)

        assert result.startswith("__METADATA__:")
        parsed = json.loads(result[len("__METADATA__:"):])
        assert parsed == usage

    def test_json_is_parseable(self):
        """Output JSON can be parsed back."""
        usage = {"prompt_tokens": 100, "completion_tokens": 50}
        result = format_metadata_marker(usage)

        json_part = result[len("__METADATA__:"):]
        parsed = json.loads(json_part)
        assert parsed == usage


class TestSortModelsByName:
    """Tests for sort_models_by_name function."""

    def test_sorts_by_name(self):
        """Models are sorted alphabetically by name."""
        models = [
            {"id": "c", "name": "Charlie"},
            {"id": "a", "name": "Alpha"},
            {"id": "b", "name": "Bravo"},
        ]

        result = sort_models_by_name(models)

        assert [m["name"] for m in result] == ["Alpha", "Bravo", "Charlie"]

    def test_uses_id_as_fallback(self):
        """Uses id when name is missing."""
        models = [
            {"id": "zebra"},
            {"id": "apple", "name": "Apple"},
            {"id": "banana"},
        ]

        result = sort_models_by_name(models)

        assert [m["id"] for m in result] == ["apple", "banana", "zebra"]

    def test_does_not_mutate_original(self):
        """Returns new list, doesn't modify input."""
        models = [{"name": "B"}, {"name": "A"}]
        original_order = [m["name"] for m in models]

        sort_models_by_name(models)

        assert [m["name"] for m in models] == original_order

    def test_empty_list(self):
        """Handles empty list."""
        assert sort_models_by_name([]) == []

    def test_case_sensitive_sort(self):
        """Sort is case-sensitive (uppercase before lowercase)."""
        models = [{"name": "beta"}, {"name": "Alpha"}, {"name": "gamma"}]

        result = sort_models_by_name(models)

        # Uppercase 'A' sorts before lowercase 'b' and 'g'
        assert [m["name"] for m in result] == ["Alpha", "beta", "gamma"]


# --- Test helpers ---

def _make_usage(prompt, completion, total):
    """Create a mock usage object."""
    class Usage:
        def __init__(self):
            self.prompt_tokens = prompt
            self.completion_tokens = completion
            self.total_tokens = total
    return Usage()


def _make_chunk(usage=None, model=None):
    """Create a mock chunk object."""
    class Chunk:
        def __init__(self):
            self.usage = usage
            self.model = model
    return Chunk()


class TestChatServiceIsConfigured:
    """Tests for ChatService.is_configured method."""

    def test_returns_true_when_api_key_set(self, app_context):
        """Returns True when OPENROUTER_API_KEY is configured."""
        from chat_rag_explorer.services import ChatService

        app_context.config["OPENROUTER_API_KEY"] = "sk-valid-api-key-12345"
        service = ChatService()

        assert service.is_configured() is True

    def test_returns_false_when_api_key_empty(self, app_context):
        """Returns False when OPENROUTER_API_KEY is empty string."""
        from chat_rag_explorer.services import ChatService

        app_context.config["OPENROUTER_API_KEY"] = ""
        service = ChatService()

        assert service.is_configured() is False

    def test_returns_false_when_api_key_none(self, app_context):
        """Returns False when OPENROUTER_API_KEY is None."""
        from chat_rag_explorer.services import ChatService

        app_context.config["OPENROUTER_API_KEY"] = None
        service = ChatService()

        assert service.is_configured() is False

    def test_returns_false_when_api_key_missing(self, app_context):
        """Returns False when OPENROUTER_API_KEY key is missing entirely."""
        from chat_rag_explorer.services import ChatService

        # Remove the key from config
        if "OPENROUTER_API_KEY" in app_context.config:
            del app_context.config["OPENROUTER_API_KEY"]
        service = ChatService()

        assert service.is_configured() is False


class TestGetModelsListStatus:
    """Tests for get_models_list_status function."""

    @pytest.fixture(autouse=True)
    def setup(self, app_context, tmp_path):
        """Set up test environment with mocked app root path."""
        # Create subdirectory to simulate app root structure
        self.app_root = tmp_path / "chat_rag_explorer"
        self.app_root.mkdir()
        self.project_root = tmp_path
        self.models_list_path = tmp_path / ".models_list"

        # Patch current_app.root_path for all tests
        patcher = patch("chat_rag_explorer.services.current_app")
        self.mock_app = patcher.start()
        self.mock_app.root_path = str(self.app_root)
        yield
        patcher.stop()

    def test_file_not_exists(self):
        """Returns exists=False when .models_list doesn't exist."""
        result = get_models_list_status()

        assert result == {"exists": False, "count": 0, "path": ".models_list"}

    def test_file_exists_with_models(self):
        """Returns exists=True and correct count when file has models."""
        self.models_list_path.write_text("openai/gpt-4\nanthropic/claude-3\ndeepseek/v3\n")

        result = get_models_list_status()

        assert result == {"exists": True, "count": 3, "path": ".models_list"}

    def test_file_with_comments_and_empty_lines(self):
        """Comments and empty lines are not counted."""
        self.models_list_path.write_text("# Comment\nopenai/gpt-4\n\nanthropic/claude-3\n")

        result = get_models_list_status()

        assert result["count"] == 2

    def test_empty_file(self):
        """Empty file returns exists=True but count=0."""
        self.models_list_path.write_text("")

        result = get_models_list_status()

        assert result == {"exists": True, "count": 0, "path": ".models_list"}

    def test_file_with_only_comments(self):
        """File with only comments returns count=0."""
        self.models_list_path.write_text("# Comment\n# Another\n")

        result = get_models_list_status()

        assert result["exists"] is True
        assert result["count"] == 0

    def test_whitespace_only_lines_not_counted(self):
        """Lines with only whitespace are not counted."""
        self.models_list_path.write_text("openai/gpt-4\n   \n\t\nanthropic/claude-3\n")

        result = get_models_list_status()

        assert result["count"] == 2
