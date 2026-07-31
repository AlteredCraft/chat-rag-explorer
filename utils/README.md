# Utils

Command-line utilities for preparing markdown content for the RAG system. You don't need these to run the app — it ships with a ready-made sample database (see the [README](../README.md)). Reach for them when you want to load your *own* documents.

## Chunking, briefly

Retrieval doesn't search whole documents; it searches **chunks**. Before your documents can be searched, they have to be cut into pieces small enough to be individually meaningful and small enough to fit in a prompt alongside the question.

Two parameters control the cut:

- **`chunk_size`** — maximum tokens per chunk (default 256). A [token](https://openrouter.ai/docs) is roughly ¾ of a word. Too small and a chunk loses the context that made it meaningful; too large and retrieval returns a lot of irrelevant text along with the good part.
- **`overlap`** — tokens each chunk repeats from the previous one (default 50). Without overlap, a sentence unlucky enough to straddle a boundary is split in half and may not match anything well.

There is no universally correct setting — it depends on your documents. That is exactly why `ingest.py` makes you look at the chunks before committing them.

## ingest.py

Ingests markdown files into ChromaDB for RAG retrieval. Uses a two-phase workflow
that lets you **inspect chunks before ingesting** to tune chunking parameters.

### Interactive Mode (Recommended)

Run without arguments for interactive mode:

```bash
uv run utils/ingest.py
```

The interactive workflow:

1. **Select corpus** - Pick from `data/corpus/` directories or enter a custom path
2. **Set parameters** - Configure chunk size and overlap (tokens)
3. **Preview chunks** - Chunks are written to `data/chunks/{corpus}/` for inspection
4. **Review & decide**:
   - `[A]` Accept - Ingest chunks to ChromaDB
   - `[R]` Re-run - Try different parameters (chunks are regenerated)
   - `[Q]` Quit - Keep chunks for later inspection

### Inspecting Chunks

Chunk preview files are human-readable markdown at `data/chunks/{corpus_name}/`:

```markdown
---
source_file: "01_PlayingTheGame.md"
chunk_size: 256
overlap: 50
total_chunks: 24
title: "Playing The Game"
---

----- chunk 0 (245 tokens) -----

First chunk content here...

----- chunk 1 (251 tokens) -----

Second chunk content here...
```

Adjust `chunk_size` and `overlap` until chunks capture meaningful semantic units.

### CLI Mode

For scripting or CI, pass arguments directly:

```bash
uv run utils/ingest.py <directory> [collection_name] [--chunk-size N] [--overlap N]
```

| Option | Description | Default |
|--------|-------------|---------|
| `directory` | Directory containing markdown files | (required) |
| `collection_name` | ChromaDB collection name | `{folder}-{chunk_size}chunk-{overlap}overlap` |
| `--chunk-size` | Maximum tokens per chunk | 256 |
| `--overlap` | Token overlap between chunks | 50 |

```bash
# Auto-generated collection name: my-docs-256chunk-50overlap
uv run utils/ingest.py ./data/corpus/my_docs

# Custom chunk size: my-docs-512chunk-100overlap
uv run utils/ingest.py ./data/corpus/my_docs --chunk-size 512 --overlap 100

# Explicit collection name
uv run utils/ingest.py ./data/corpus/my_docs my_collection
```

### How It Works

1. Recursively finds all `.md` files in the directory (skips files starting with `_`)
2. Extracts YAML frontmatter as metadata
3. Chunks content using token-based splitting (matching the embedding model's tokenizer)
4. Stores chunks in ChromaDB at `./data/chroma_db/`

> **Tip**: Use underscore-prefixed files (e.g., `_README.md`, `_canon_bible.md`) for reference documents you don't want ingested into the vector database.

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

# 2. Ingest the chapters (interactive mode recommended)
uv run utils/ingest.py
```

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
