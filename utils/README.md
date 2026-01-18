# Utils

Command-line utilities for preparing markdown content for the RAG system.

## split.py

Splits a single markdown file into multiple chapter files based on heading patterns.

### Usage

```bash
uv run utils/split.py <input.md> [--out DIR] [--pattern PATTERN] [--fm key:value ...]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `input` | Path to the markdown file to split | (required) |
| `--out` | Output directory | `./data/{filename}/` |
| `--pattern` | Heading pattern to split on | `##` |
| `--fm` | Add frontmatter field (repeatable) | none |

### Examples

```bash
# Split on ## headings (default)
uv run utils/split.py book.md

# Split on ### headings with custom output
uv run utils/split.py book.md --pattern "###" --out ./chapters/

# Add custom frontmatter to all chapters
uv run utils/split.py book.md \
  --fm title:"My Book" \
  --fm author:"Jane Doe" \
  --fm url:"https://example.com"
```

### Output

Creates numbered markdown files with YAML frontmatter:

```
01_chapter_one.md
02_chapter_two.md
...
```

Each file includes:
```yaml
---
section_number: 1
section_title: "Chapter One"
title: "My Book"        # from --fm
author: "Jane Doe"      # from --fm
---
```

---

## ingest.py

Ingests markdown files into ChromaDB for RAG retrieval. Automatically chunks content
using token-based splitting optimized for the embedding model.

### Usage

```bash
uv run utils/ingest.py <directory> [collection_name] [--no-chunk] [--chunk-size N] [--overlap N]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `directory` | Directory containing markdown files | (required) |
| `collection_name` | ChromaDB collection name | `{folder}-{chunk_size}chunk-{overlap}overlap` |
| `--no-chunk` | Ingest whole documents without chunking | false |
| `--chunk-size` | Maximum tokens per chunk | 256 |
| `--overlap` | Token overlap between chunks | 50 |

### Examples

```bash
# Ingest with auto-generated collection name (my-docs-256chunk-50overlap)
uv run utils/ingest.py ./data/corpus/my_docs

# Ingest with explicit collection name
uv run utils/ingest.py ./data/corpus/my_docs my_collection

# Ingest without chunking (for short documents)
uv run utils/ingest.py ./data/corpus/my_docs my_collection --no-chunk

# Custom chunk size (auto-generates: my-docs-512chunk-100overlap)
uv run utils/ingest.py ./data/corpus/my_docs --chunk-size 512 --overlap 100
```

### How It Works

1. Recursively finds all `.md` files in the directory
2. Extracts YAML frontmatter as metadata
3. Chunks content using token-based splitting (configurable size and overlap)
4. Stores chunks in ChromaDB at `./data/chroma_db/`

### Metadata

Each chunk stored in ChromaDB includes:
- `source_file`: Relative path to the original file
- `chunk_index`: Position of this chunk (0-indexed)
- `total_chunks`: Total chunks from this file
- All frontmatter fields from the markdown file

### Typical Workflow

```bash
# 1. Split a large book into chapters
uv run utils/split.py "My Book.md" --pattern "##" \
  --fm title:"My Book" --fm author:"Author Name"

# 2. Ingest the chapters into ChromaDB
uv run utils/ingest.py ./data/my_book my_book_collection
```
