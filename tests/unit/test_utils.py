"""
Unit tests for utils.py shared helpers.
"""
from chat_rag_explorer.utils import mask_api_key


class TestMaskApiKey:
    """Tests for mask_api_key function."""

    def test_masks_long_key(self):
        """Long API keys show first 8 and last 4 chars."""
        key = "sk-1234567890abcdefghij"
        assert mask_api_key(key) == "sk-12345...ghij"

    def test_masks_exactly_13_chars(self):
        """Keys with exactly 13 chars show first 8 and last 4."""
        key = "1234567890123"
        assert mask_api_key(key) == "12345678...0123"

    def test_short_key_fully_masked(self):
        """Keys with 12 or fewer chars are fully masked (too short to excerpt)."""
        assert mask_api_key("123456789012") == "****"
        assert mask_api_key("short") == "****"

    def test_empty_string_returns_missing(self):
        """Empty string returns [MISSING]."""
        assert mask_api_key("") == "[MISSING]"

    def test_none_returns_missing(self):
        """None returns [MISSING]."""
        assert mask_api_key(None) == "[MISSING]"
