"""
Unit tests for prompt_service.py.

Tests prompt loading, parsing, CRUD operations, and caching behavior.
All file operations use tmp_path fixture to avoid touching real prompts.
"""
import pytest
from chat_rag_explorer.prompt_service import PromptService, DEFAULT_PROMPT_ID, DEFAULT_PROMPT


class TestDefaultPrompt:
    """Tests for the default prompt content."""

    def test_default_prompt_includes_citation_instructions(self):
        """Default prompt instructs LLM to cite sources with inline references."""
        assert "[1]" in DEFAULT_PROMPT['content']
        assert "sources" in DEFAULT_PROMPT['content'].lower()


class TestParseFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_parse_valid_frontmatter(self):
        """Parse complete frontmatter with title and description."""
        service = PromptService()
        content = '''---
title: "Test Title"
description: "Test Description"
---
This is the body content.'''

        metadata, body = service._parse_frontmatter(content)

        assert metadata["title"] == "Test Title"
        assert metadata["description"] == "Test Description"
        assert body == "This is the body content."

    def test_parse_frontmatter_no_quotes(self):
        """Parse frontmatter values without quotes."""
        service = PromptService()
        content = '''---
title: Simple Title
description: Simple Description
---
Body here.'''

        metadata, body = service._parse_frontmatter(content)

        assert metadata["title"] == "Simple Title"
        assert metadata["description"] == "Simple Description"

    def test_parse_no_frontmatter(self):
        """Content without frontmatter returns empty metadata."""
        service = PromptService()
        content = "Just plain content without frontmatter."

        metadata, body = service._parse_frontmatter(content)

        assert metadata == {}
        assert body == "Just plain content without frontmatter."

    def test_parse_multiline_body(self):
        """Body content preserves multiple lines."""
        service = PromptService()
        content = '''---
title: "Multi"
---
Line 1
Line 2
Line 3'''

        metadata, body = service._parse_frontmatter(content)

        assert "Line 1" in body
        assert "Line 2" in body
        assert "Line 3" in body


class TestGetPrompts:
    """Tests for get_prompts() method."""

    def test_includes_default_prompt(self, tmp_path, monkeypatch):
        """Default protected prompt is always included."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        prompts = service.get_prompts()

        default = next((p for p in prompts if p["id"] == DEFAULT_PROMPT_ID), None)
        assert default is not None
        assert default["protected"] is True

    def test_loads_md_files(self, tmp_path, monkeypatch):
        """Loads .md files from prompts directory."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        # Create a test prompt file
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text('''---
title: "Test Prompt"
description: "A test"
---
Test content here.''')

        prompts = service.get_prompts()

        test_prompt = next((p for p in prompts if p["id"] == "test_prompt"), None)
        assert test_prompt is not None
        assert test_prompt["title"] == "Test Prompt"
        assert test_prompt["content"] == "Test content here."
        assert test_prompt["protected"] is False

    def test_caches_loaded_prompts(self, tmp_path, monkeypatch):
        """Loaded prompts are cached by mtime."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        prompt_file = tmp_path / "cached.md"
        prompt_file.write_text('''---
title: "Cached"
---
Content.''')

        # First load
        service.get_prompts()
        assert "cached" in service._cache

        # Second load should use cache
        service.get_prompts()
        assert "cached" in service._cache

    def test_empty_directory_returns_only_default(self, tmp_path, monkeypatch):
        """Empty prompts directory returns only default prompt."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        prompts = service.get_prompts()

        assert len(prompts) == 1
        assert prompts[0]["id"] == DEFAULT_PROMPT_ID

    def test_nonexistent_directory_returns_default(self, tmp_path, monkeypatch):
        """Nonexistent directory returns only default prompt."""
        service = PromptService()
        nonexistent = tmp_path / "does_not_exist"
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: nonexistent)

        prompts = service.get_prompts()

        assert len(prompts) == 1
        assert prompts[0]["id"] == DEFAULT_PROMPT_ID


class TestGetPromptById:
    """Tests for get_prompt_by_id() method."""

    def test_get_default_prompt(self):
        """Can retrieve the default protected prompt."""
        service = PromptService()

        prompt = service.get_prompt_by_id(DEFAULT_PROMPT_ID)

        assert prompt is not None
        assert prompt["id"] == DEFAULT_PROMPT_ID
        assert prompt["protected"] is True

    def test_get_existing_prompt(self, tmp_path, monkeypatch):
        """Can retrieve an existing prompt by ID."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        prompt_file = tmp_path / "my_prompt.md"
        prompt_file.write_text('''---
title: "My Prompt"
---
My content.''')

        prompt = service.get_prompt_by_id("my_prompt")

        assert prompt is not None
        assert prompt["id"] == "my_prompt"
        assert prompt["title"] == "My Prompt"

    def test_get_nonexistent_prompt(self, tmp_path, monkeypatch):
        """Returns None for nonexistent prompt ID."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        prompt = service.get_prompt_by_id("does_not_exist")

        assert prompt is None


class TestIsProtected:
    """Tests for is_protected() method."""

    def test_default_prompt_is_protected(self):
        """Default prompt ID is protected."""
        service = PromptService()

        assert service.is_protected(DEFAULT_PROMPT_ID) is True

    def test_custom_prompt_not_protected(self):
        """Custom prompt IDs are not protected."""
        service = PromptService()

        assert service.is_protected("custom_prompt") is False


class TestSavePrompt:
    """Tests for save_prompt() method."""

    def test_save_new_prompt(self, tmp_path, monkeypatch):
        """Can save a new prompt to file."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        result = service.save_prompt(
            "new_prompt",
            "New Title",
            "New Description",
            "New content here."
        )

        assert result is not None
        assert result["id"] == "new_prompt"
        assert (tmp_path / "new_prompt.md").exists()

    def test_save_updates_existing(self, tmp_path, monkeypatch):
        """Saving to existing ID updates the file."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        # Create initial
        service.save_prompt("existing", "Original", "", "Original content")

        # Update
        result = service.save_prompt("existing", "Updated", "", "Updated content")

        assert result["title"] == "Updated"
        assert result["content"] == "Updated content"

    def test_cannot_save_protected_prompt(self, tmp_path, monkeypatch):
        """Cannot save to protected prompt ID."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        result = service.save_prompt(
            DEFAULT_PROMPT_ID,
            "Hacked",
            "",
            "Malicious content"
        )

        assert result is None

    def test_save_invalidates_cache(self, tmp_path, monkeypatch):
        """Saving prompt invalidates its cache entry."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        # Create and cache
        service.save_prompt("cached", "Original", "", "Original")
        service.get_prompt_by_id("cached")
        assert "cached" in service._cache

        # Save again - should invalidate
        service.save_prompt("cached", "Updated", "", "Updated")
        assert "cached" not in service._cache


class TestDeletePrompt:
    """Tests for delete_prompt() method."""

    def test_delete_existing_prompt(self, tmp_path, monkeypatch):
        """Can delete an existing prompt."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        # Create
        service.save_prompt("to_delete", "Title", "", "Content")
        assert (tmp_path / "to_delete.md").exists()

        # Delete
        result = service.delete_prompt("to_delete")

        assert result is True
        assert not (tmp_path / "to_delete.md").exists()

    def test_cannot_delete_protected_prompt(self):
        """Cannot delete protected prompt."""
        service = PromptService()

        result = service.delete_prompt(DEFAULT_PROMPT_ID)

        assert result is False

    def test_delete_nonexistent_returns_false(self, tmp_path, monkeypatch):
        """Deleting nonexistent prompt returns False."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        result = service.delete_prompt("does_not_exist")

        assert result is False

    def test_delete_removes_from_cache(self, tmp_path, monkeypatch):
        """Deleting prompt removes it from cache."""
        service = PromptService()
        monkeypatch.setattr(service, "_get_prompts_dir", lambda: tmp_path)

        # Create and cache
        service.save_prompt("cached", "Title", "", "Content")
        service.get_prompt_by_id("cached")
        assert "cached" in service._cache

        # Delete
        service.delete_prompt("cached")
        assert "cached" not in service._cache
