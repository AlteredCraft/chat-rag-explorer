"""
Unit tests for utils/ingest.py markdown ingestion module.

Tests cover:
- Markdown file discovery
- Frontmatter parsing
- Token-based chunking
- Error handling for malformed files
"""

import pytest
from unittest.mock import MagicMock

from utils.ingest import (
    find_markdown_files,
    parse_markdown,
    chunk_by_tokens,
    ingest_file,
    count_tokens,
    sanitize_collection_name,
    ParseError,
)


class TestSanitizeCollectionName:
    """Tests for sanitize_collection_name function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # Lowercase conversion
            ("MyFolder", "myfolder"),
            ("UPPERCASE", "uppercase"),
            # Spaces to hyphens
            ("my folder", "my-folder"),
            ("multiple spaces here", "multiple-spaces-here"),
            # Underscores to hyphens
            ("my_folder", "my-folder"),
            ("snake_case_name", "snake-case-name"),
            # Preserves hyphens
            ("pg-essays", "pg-essays"),
            ("already-hyphenated", "already-hyphenated"),
            # Removes special characters
            ("my@folder!", "myfolder"),
            ("test#123", "test123"),
            # Collapses multiple hyphens
            ("my--folder", "my-folder"),
            ("my - folder", "my-folder"),
            ("too---many----hyphens", "too-many-hyphens"),
            # Strips leading/trailing hyphens
            ("-folder-", "folder"),
            ("--folder--", "folder"),
            # Complex names
            ("My Folder (2024)", "my-folder-2024"),
            ("Paul Graham's Essays!", "paul-grahams-essays"),
        ],
    )
    def test_sanitizes_name(self, input_name, expected):
        """Should sanitize folder names for ChromaDB collection names."""
        assert sanitize_collection_name(input_name) == expected


class TestFindMarkdownFiles:
    """Tests for find_markdown_files function."""

    def test_finds_markdown_files(self, tmp_path):
        """Should find all .md files in directory."""
        (tmp_path / "file1.md").write_text("# Test 1")
        (tmp_path / "file2.md").write_text("# Test 2")
        (tmp_path / "other.txt").write_text("Not markdown")

        result = find_markdown_files(tmp_path)

        assert len(result) == 2
        assert all(f.suffix == ".md" for f in result)

    def test_finds_nested_markdown_files(self, tmp_path):
        """Should recursively find .md files in subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.md").write_text("# Root")
        (subdir / "nested.md").write_text("# Nested")

        result = find_markdown_files(tmp_path)

        assert len(result) == 2

    def test_returns_empty_list_for_no_markdown(self, tmp_path):
        """Should return empty list when no .md files exist."""
        (tmp_path / "file.txt").write_text("Not markdown")

        result = find_markdown_files(tmp_path)

        assert result == []

    def test_returns_sorted_results(self, tmp_path):
        """Should return files sorted by path."""
        (tmp_path / "b.md").write_text("# B")
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "c.md").write_text("# C")

        result = find_markdown_files(tmp_path)

        names = [f.name for f in result]
        assert names == ["a.md", "b.md", "c.md"]


class TestParseMarkdown:
    """Tests for parse_markdown function."""

    def test_parses_frontmatter_and_content(self, tmp_path):
        """Should extract frontmatter metadata and content."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""---
title: "Test Title"
author: "Test Author"
---

# Content Here

Some body text.
""")

        metadata, content = parse_markdown(md_file)

        assert metadata["title"] == "Test Title"
        assert metadata["author"] == "Test Author"
        assert "# Content Here" in content
        assert "Some body text." in content

    def test_handles_no_frontmatter(self, tmp_path):
        """Should handle markdown without frontmatter."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Just Content\n\nNo frontmatter here.")

        metadata, content = parse_markdown(md_file)

        assert metadata == {}
        assert "# Just Content" in content

    def test_handles_list_metadata(self, tmp_path):
        """Should handle list values in frontmatter."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""---
tags: ["python", "testing"]
---

Content here.
""")

        metadata, _ = parse_markdown(md_file)

        assert metadata["tags"] == ["python", "testing"]

    def test_raises_parse_error_for_malformed_yaml(self, tmp_path):
        """Should raise ParseError for malformed YAML frontmatter."""
        md_file = tmp_path / "bad.md"
        md_file.write_text("""---
title: "Unmatched "quotes" here"
---

Content.
""")

        with pytest.raises(ParseError) as exc_info:
            parse_markdown(md_file)

        assert "Failed to parse" in str(exc_info.value)


class TestChunkByTokens:
    """Tests for chunk_by_tokens function."""

    def test_short_content_single_chunk(self):
        """Short content should return single chunk."""
        content = "This is a short piece of text."

        chunks = chunk_by_tokens(content, chunk_size=256, overlap=50)

        assert len(chunks) == 1
        assert chunks[0] == content

    @pytest.mark.parametrize("content", ["", "   ", "\n", "\t\n  "])
    def test_empty_content_returns_empty_list(self, content):
        """Empty or whitespace-only content should return empty list."""
        assert chunk_by_tokens(content) == []

    def test_long_content_creates_multiple_chunks(self):
        """Long content should be split into multiple chunks."""
        # Create content that will exceed chunk_size
        content = " ".join(["word"] * 500)

        chunks = chunk_by_tokens(content, chunk_size=100, overlap=20)

        assert len(chunks) > 1

    def test_chunks_respect_size_limit(self):
        """Each chunk should be under the token limit."""
        content = " ".join(["testing"] * 500)

        chunks = chunk_by_tokens(content, chunk_size=100, overlap=20)

        for chunk in chunks:
            token_count = count_tokens(chunk)
            # Allow some tolerance for tokenizer behavior
            assert token_count <= 110, f"Chunk has {token_count} tokens"

    def test_overlap_creates_redundancy(self):
        """Chunks should have overlapping content."""
        content = " ".join([f"word{i}" for i in range(200)])

        chunks = chunk_by_tokens(content, chunk_size=50, overlap=10)

        # With overlap, later chunks should contain some content from earlier chunks
        if len(chunks) > 1:
            # Check that consecutive chunks share some words
            chunk0_words = set(chunks[0].split())
            chunk1_words = set(chunks[1].split())
            overlap_words = chunk0_words & chunk1_words
            assert len(overlap_words) > 0, "Chunks should have overlapping content"


class TestCountTokens:
    """Tests for count_tokens function."""

    def test_counts_tokens_in_text(self):
        """Should return positive token count for text."""
        count = count_tokens("Hello world, this is a test.")
        assert count > 0

    def test_empty_string_returns_small_count(self):
        """Empty string should return minimal tokens (special tokens only)."""
        count = count_tokens("")
        assert count <= 2  # May include [CLS] and [SEP] special tokens


class TestIngestFile:
    """Tests for ingest_file function."""

    def test_ingests_file_into_collection(self, tmp_path):
        """Should add document chunks to collection."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""---
title: "Test Doc"
---

This is test content for ingestion.
""")

        mock_collection = MagicMock()

        chunks_added = ingest_file(md_file, mock_collection, base_dir=tmp_path)

        assert chunks_added > 0
        mock_collection.add.assert_called_once()

        # Verify the call arguments
        call_kwargs = mock_collection.add.call_args[1]
        assert len(call_kwargs["ids"]) == chunks_added
        assert len(call_kwargs["documents"]) == chunks_added
        assert len(call_kwargs["metadatas"]) == chunks_added

    def test_includes_metadata_in_chunks(self, tmp_path):
        """Should include frontmatter and chunk metadata."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""---
title: "My Title"
author: "Test Author"
---

Content here.
""")

        mock_collection = MagicMock()

        ingest_file(md_file, mock_collection, base_dir=tmp_path)

        call_kwargs = mock_collection.add.call_args[1]
        metadata = call_kwargs["metadatas"][0]

        assert metadata["title"] == "My Title"
        assert metadata["author"] == "Test Author"
        assert metadata["source_file"] == "test.md"
        assert metadata["chunk_index"] == 0

    def test_no_chunk_mode_single_document(self, tmp_path):
        """With no_chunk=True, should ingest entire document as one chunk."""
        md_file = tmp_path / "test.md"
        content = " ".join(["word"] * 500)  # Long content
        md_file.write_text(f"---\ntitle: Test\n---\n\n{content}")

        mock_collection = MagicMock()

        chunks_added = ingest_file(
            md_file, mock_collection, base_dir=tmp_path, no_chunk=True
        )

        assert chunks_added == 1

    def test_skips_empty_content(self, tmp_path):
        """Should skip files with no content."""
        md_file = tmp_path / "empty.md"
        md_file.write_text("""---
title: "Empty Doc"
---

""")

        mock_collection = MagicMock()

        chunks_added = ingest_file(md_file, mock_collection, base_dir=tmp_path)

        assert chunks_added == 0
        mock_collection.add.assert_not_called()

    def test_handles_parse_error_gracefully(self, tmp_path):
        """Should return 0 for files that fail to parse."""
        md_file = tmp_path / "bad.md"
        md_file.write_text("""---
title: "Bad "nested" quotes"
---

Content.
""")

        mock_collection = MagicMock()

        chunks_added = ingest_file(md_file, mock_collection, base_dir=tmp_path)

        assert chunks_added == 0
        mock_collection.add.assert_not_called()

    def test_respects_chunk_size_parameter(self, tmp_path):
        """Should use provided chunk_size parameter."""
        md_file = tmp_path / "test.md"
        content = " ".join(["word"] * 500)
        md_file.write_text(f"---\ntitle: Test\n---\n\n{content}")

        mock_collection = MagicMock()

        # Small chunk size should create more chunks
        chunks_small = ingest_file(
            md_file, mock_collection, base_dir=tmp_path, chunk_size=50, overlap=10
        )

        mock_collection.reset_mock()

        # Large chunk size should create fewer chunks
        chunks_large = ingest_file(
            md_file, mock_collection, base_dir=tmp_path, chunk_size=200, overlap=10
        )

        assert chunks_small > chunks_large

    def test_list_metadata_converted_to_string(self, tmp_path):
        """List metadata values should be joined as comma-separated string."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""---
tags: ["python", "testing", "rag"]
---

Content here.
""")

        mock_collection = MagicMock()

        ingest_file(md_file, mock_collection, base_dir=tmp_path)

        call_kwargs = mock_collection.add.call_args[1]
        metadata = call_kwargs["metadatas"][0]

        assert metadata["tags"] == "python, testing, rag"
