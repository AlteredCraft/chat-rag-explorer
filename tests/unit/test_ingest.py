"""
Unit tests for utils/ingest.py markdown ingestion module.

Tests cover:
- Markdown file discovery
- Frontmatter parsing
- Token-based chunking
- Collection name sanitization
- Corpus directory listing (interactive mode)
- Two-phase chunk file operations (write, read, manifest)
- Error handling for malformed files
"""

from pathlib import Path

import pytest
from unittest.mock import MagicMock

from utils.ingest import (
    find_markdown_files,
    parse_markdown,
    chunk_by_tokens,
    ingest_file,
    count_tokens,
    sanitize_collection_name,
    get_corpus_directories,
    get_directory_stats,
    format_file_size,
    clear_chunks_dir,
    write_chunk_file,
    write_manifest,
    read_manifest,
    read_chunk_files,
    parse_chunk_markdown,
    create_chunks_to_files,
    CHUNKS_DIR,
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


class TestGetCorpusDirectories:
    """Tests for get_corpus_directories function."""

    def test_returns_empty_when_corpus_dir_missing(self, tmp_path, monkeypatch):
        """Should return empty list when data/corpus doesn't exist."""
        # Point the function to a non-existent corpus dir
        fake_ingest_path = tmp_path / "utils" / "ingest.py"
        fake_ingest_path.parent.mkdir(parents=True)
        fake_ingest_path.touch()

        import utils.ingest as ingest_module

        # Monkeypatch __file__ to point to our fake path
        monkeypatch.setattr(ingest_module, "__file__", str(fake_ingest_path))

        result = get_corpus_directories()

        assert result == []

    def test_returns_only_directories(self, tmp_path, monkeypatch):
        """Should return directories only, not files."""
        # Create fake corpus structure
        corpus_dir = tmp_path / "data" / "corpus"
        corpus_dir.mkdir(parents=True)

        # Create directories
        (corpus_dir / "dir_one").mkdir()
        (corpus_dir / "dir_two").mkdir()

        # Create a file (should be excluded)
        (corpus_dir / "readme.txt").touch()

        # Point function to our fake structure
        fake_ingest_path = tmp_path / "utils" / "ingest.py"
        fake_ingest_path.parent.mkdir(parents=True)
        fake_ingest_path.touch()

        import utils.ingest as ingest_module

        monkeypatch.setattr(ingest_module, "__file__", str(fake_ingest_path))

        result = get_corpus_directories()

        assert len(result) == 2
        assert all(d.is_dir() for d in result)
        assert {d.name for d in result} == {"dir_one", "dir_two"}

    def test_returns_sorted_directories(self, tmp_path, monkeypatch):
        """Should return directories in sorted order."""
        corpus_dir = tmp_path / "data" / "corpus"
        corpus_dir.mkdir(parents=True)

        # Create directories in non-alphabetical order
        (corpus_dir / "zebra").mkdir()
        (corpus_dir / "alpha").mkdir()
        (corpus_dir / "middle").mkdir()

        fake_ingest_path = tmp_path / "utils" / "ingest.py"
        fake_ingest_path.parent.mkdir(parents=True)
        fake_ingest_path.touch()

        import utils.ingest as ingest_module

        monkeypatch.setattr(ingest_module, "__file__", str(fake_ingest_path))

        result = get_corpus_directories()

        names = [d.name for d in result]
        assert names == ["alpha", "middle", "zebra"]


class TestFormatFileSize:
    """Tests for format_file_size function."""

    @pytest.mark.parametrize(
        "size_bytes,expected",
        [
            (0, "0 B"),
            (512, "512 B"),
            (1023, "1023 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1024 * 100, "100.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1.5, "1.5 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
        ],
    )
    def test_formats_sizes_correctly(self, size_bytes, expected):
        """Should format various sizes to human-readable strings."""
        assert format_file_size(int(size_bytes)) == expected


class TestGetDirectoryStats:
    """Tests for get_directory_stats function."""

    def test_counts_markdown_files_and_size(self, tmp_path):
        """Should count .md files and sum their sizes."""
        # Create test markdown files
        (tmp_path / "file1.md").write_text("Hello world")  # 11 bytes
        (tmp_path / "file2.md").write_text("More content here")  # 17 bytes
        (tmp_path / "ignored.txt").write_text("Not markdown")  # Should be ignored

        file_count, total_size = get_directory_stats(tmp_path)

        assert file_count == 2
        assert total_size == 28  # 11 + 17

    def test_counts_nested_files(self, tmp_path):
        """Should recursively count files in subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.md").write_text("Root file")  # 9 bytes
        (subdir / "nested.md").write_text("Nested file")  # 11 bytes

        file_count, total_size = get_directory_stats(tmp_path)

        assert file_count == 2
        assert total_size == 20

    def test_empty_directory(self, tmp_path):
        """Should return zeros for empty directory."""
        file_count, total_size = get_directory_stats(tmp_path)

        assert file_count == 0
        assert total_size == 0


class TestClearChunksDir:
    """Tests for clear_chunks_dir function."""

    def test_creates_new_directory(self, tmp_path, monkeypatch):
        """Should create chunks directory if it doesn't exist."""
        import utils.ingest as ingest_module

        monkeypatch.setattr(ingest_module, "CHUNKS_DIR", tmp_path / "chunks")

        result = clear_chunks_dir("test-corpus")

        assert result.exists()
        assert result.is_dir()
        assert result.name == "test-corpus"

    def test_clobbers_existing_directory(self, tmp_path, monkeypatch):
        """Should remove existing contents when clearing."""
        import utils.ingest as ingest_module

        chunks_base = tmp_path / "chunks"
        chunks_base.mkdir()
        corpus_dir = chunks_base / "test-corpus"
        corpus_dir.mkdir()

        # Create some existing files
        (corpus_dir / "old_file.json").write_text("old content")
        (corpus_dir / "subdir").mkdir()

        monkeypatch.setattr(ingest_module, "CHUNKS_DIR", chunks_base)

        result = clear_chunks_dir("test-corpus")

        assert result.exists()
        assert list(result.iterdir()) == []  # Directory should be empty


class TestWriteChunkFile:
    """Tests for write_chunk_file function."""

    def test_writes_chunk_file_as_markdown(self, tmp_path):
        """Should write chunk data as readable markdown with frontmatter."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        chunks = [
            {"index": 0, "token_count": 100, "text": "First chunk"},
            {"index": 1, "token_count": 95, "text": "Second chunk"},
        ]
        metadata = {"title": "Test Doc", "author": "Test Author"}
        params = {"chunk_size": 256, "overlap": 50}

        result = write_chunk_file(
            chunks_dir,
            file_index=0,
            source_file="test.md",
            metadata=metadata,
            params=params,
            chunks=chunks,
        )

        assert result.exists()
        assert result.name == "00_test.chunks.md"

        content = result.read_text()

        # Check frontmatter
        assert "---" in content
        assert 'source_file: "test.md"' in content
        assert "chunk_size: 256" in content
        assert "overlap: 50" in content
        assert "total_chunks: 2" in content
        assert 'title: "Test Doc"' in content

        # Check chunk delimiters
        assert "----- chunk 0 (100 tokens) -----" in content
        assert "----- chunk 1 (95 tokens) -----" in content
        assert "First chunk" in content
        assert "Second chunk" in content

    def test_filename_includes_index_and_stem(self, tmp_path):
        """Should create filename with index and source file stem."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        result = write_chunk_file(
            chunks_dir,
            file_index=5,
            source_file="chapter_one.md",
            metadata={},
            params={"chunk_size": 256, "overlap": 50},
            chunks=[{"index": 0, "token_count": 50, "text": "content"}],
        )

        assert result.name == "05_chapter_one.chunks.md"


class TestWriteAndReadManifest:
    """Tests for write_manifest and read_manifest functions."""

    def test_roundtrip_manifest(self, tmp_path):
        """Should write and read manifest correctly."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        params = {"chunk_size": 256, "overlap": 50}
        stats = {"total_files": 10, "total_chunks": 150, "total_tokens": 35000}

        write_manifest(
            chunks_dir,
            corpus_name="test-corpus",
            source_dir="/path/to/source",
            params=params,
            stats=stats,
        )

        result = read_manifest(chunks_dir)

        assert result["corpus_name"] == "test-corpus"
        assert result["source_dir"] == "/path/to/source"
        assert result["params"] == params
        assert result["summary"] == stats
        assert "created_at" in result

    def test_read_missing_manifest_returns_none(self, tmp_path):
        """Should return None if manifest doesn't exist."""
        result = read_manifest(tmp_path)
        assert result is None


class TestReadChunkFiles:
    """Tests for read_chunk_files function."""

    def _write_chunk_md(self, path: Path, source_file: str, chunks: list[dict] = None):
        """Helper to write a chunk markdown file for testing."""
        chunks = chunks or []
        lines = [
            "---",
            f'source_file: "{source_file}"',
            "chunk_size: 256",
            "overlap: 50",
            f"total_chunks: {len(chunks)}",
            "---",
            "",
        ]
        for chunk in chunks:
            lines.append(f"----- chunk {chunk['index']} ({chunk['token_count']} tokens) -----")
            lines.append("")
            lines.append(chunk["text"])
            lines.append("")
        path.write_text("\n".join(lines))

    def test_reads_all_chunk_files_sorted(self, tmp_path):
        """Should read all .chunks.md files in sorted order."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        # Create chunk files out of order
        for i, name in [(2, "charlie"), (0, "alpha"), (1, "bravo")]:
            self._write_chunk_md(
                chunks_dir / f"{i:02d}_{name}.chunks.md",
                f"{name}.md",
            )

        results = read_chunk_files(chunks_dir)

        assert len(results) == 3
        assert results[0]["source_file"] == "alpha.md"
        assert results[1]["source_file"] == "bravo.md"
        assert results[2]["source_file"] == "charlie.md"

    def test_ignores_non_chunk_files(self, tmp_path):
        """Should only read .chunks.md files."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        # Create a chunk file
        self._write_chunk_md(
            chunks_dir / "00_test.chunks.md",
            "test.md",
        )

        # Create other files that should be ignored
        (chunks_dir / "manifest.json").write_text("{}")
        (chunks_dir / "notes.txt").write_text("notes")

        results = read_chunk_files(chunks_dir)

        assert len(results) == 1
        assert results[0]["source_file"] == "test.md"


class TestParseChunkMarkdown:
    """Tests for parse_chunk_markdown function."""

    def test_parses_frontmatter_and_chunks(self):
        """Should parse markdown chunk file into structured data."""
        content = '''---
source_file: "test.md"
chunk_size: 256
overlap: 50
total_chunks: 2
title: "Test Doc"
---

----- chunk 0 (10 tokens) -----

First chunk content.

----- chunk 1 (15 tokens) -----

Second chunk content.
'''
        result = parse_chunk_markdown(content)

        assert result["source_file"] == "test.md"
        assert result["params"]["chunk_size"] == 256
        assert result["params"]["overlap"] == 50
        assert result["total_chunks"] == 2
        assert result["metadata"]["title"] == "Test Doc"
        assert len(result["chunks"]) == 2
        assert result["chunks"][0]["index"] == 0
        assert result["chunks"][0]["token_count"] == 10
        assert result["chunks"][0]["text"] == "First chunk content."
        assert result["chunks"][1]["index"] == 1
        assert result["chunks"][1]["token_count"] == 15
        assert result["chunks"][1]["text"] == "Second chunk content."

    def test_raises_on_missing_frontmatter(self):
        """Should raise ValueError if frontmatter is missing."""
        content = "No frontmatter here"
        with pytest.raises(ValueError, match="missing frontmatter"):
            parse_chunk_markdown(content)

    def test_roundtrip_with_write_chunk_file(self, tmp_path):
        """Should be able to read back what write_chunk_file produces."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        source_file = "doc.md"
        metadata = {"title": "Test Document", "author": "Test Author"}
        params = {"chunk_size": 256, "overlap": 50}
        chunks = [
            {"index": 0, "token_count": 100, "text": "First chunk text here."},
            {"index": 1, "token_count": 120, "text": "Second chunk text here."},
        ]

        # Write using write_chunk_file
        chunk_path = write_chunk_file(chunks_dir, 0, source_file, metadata, params, chunks)

        # Read back and parse
        content = chunk_path.read_text()
        result = parse_chunk_markdown(content)

        assert result["source_file"] == source_file
        assert result["params"]["chunk_size"] == 256
        assert result["params"]["overlap"] == 50
        assert result["metadata"]["title"] == "Test Document"
        assert result["metadata"]["author"] == "Test Author"
        assert len(result["chunks"]) == 2
        assert result["chunks"][0]["text"] == "First chunk text here."
        assert result["chunks"][1]["text"] == "Second chunk text here."


class TestCreateChunksToFiles:
    """Tests for create_chunks_to_files function."""

    def test_creates_chunks_and_manifest(self, tmp_path, monkeypatch):
        """Should create chunk files and manifest for markdown directory."""
        import utils.ingest as ingest_module

        # Set up source directory
        source_dir = tmp_path / "corpus" / "test-docs"
        source_dir.mkdir(parents=True)

        (source_dir / "doc1.md").write_text("""---
title: "Document 1"
---

This is the content of document one.
""")
        (source_dir / "doc2.md").write_text("""---
title: "Document 2"
---

This is the content of document two.
""")

        # Set up chunks directory
        chunks_base = tmp_path / "chunks"
        monkeypatch.setattr(ingest_module, "CHUNKS_DIR", chunks_base)

        result = create_chunks_to_files(source_dir, chunk_size=256, overlap=50)

        assert result["files_processed"] == 2
        assert result["total_chunks"] >= 2  # At least 1 chunk per file
        assert "chunks_dir" in result

        # Verify manifest exists
        chunks_dir = chunks_base / "test-docs"
        manifest = read_manifest(chunks_dir)
        assert manifest is not None
        assert manifest["corpus_name"] == "test-docs"

        # Verify chunk files exist
        chunk_files = list(chunks_dir.glob("*.chunks.md"))
        assert len(chunk_files) == 2
