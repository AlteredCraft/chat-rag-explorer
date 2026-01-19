"""
Markdown ingestion module for ChromaDB RAG system.

This module demonstrates the key steps in building a RAG (Retrieval-Augmented
Generation) pipeline: loading documents, chunking them into manageable pieces,
and storing them in a vector database for semantic search.

Key Concepts:
- Document Chunking: LLMs have context limits, so we split documents into
  smaller chunks. Overlapping chunks help preserve context at boundaries.
- Token-Based Splitting: We count tokens (not characters) because embedding
  models have token limits. Uses the same tokenizer as the embedding model.
- Metadata Extraction: YAML frontmatter becomes searchable metadata in ChromaDB,
  enabling filtered queries (e.g., "search only in chapter 3").
- Vector Embeddings: ChromaDB automatically generates embeddings using its
  default model (all-MiniLM-L6-v2) when documents are added.

Typical Workflow:
1. Prepare markdown files with optional YAML frontmatter
2. Run this script to chunk and ingest into ChromaDB
3. Query the collection using semantic search in your application

See utils/README.md for usage examples.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from chromadb import PersistentClient
import frontmatter


from tokenizers import Tokenizer

RAG_DB_FILE_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
CHUNKS_DIR = Path(__file__).parent.parent / "data" / "chunks"

# Initialize tokenizer globally to avoid reloading it for every file
# We use the same model as ChromaDB's default embedding function
try:
    TOKENIZER = Tokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    # Disable padding to get actual token counts
    TOKENIZER.no_padding()
    # Disable truncation to count all tokens
    TOKENIZER.no_truncation()
except Exception as e:
    print(f"Warning: Could not load tokenizer: {e}")
    TOKENIZER = None


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a string using the global tokenizer.
    
    Args:
        text: The text to count tokens for
        
    Returns:
        Number of tokens, or 0 if tokenizer is not available
    """
    if not TOKENIZER:
        return 0
    
    try:
        encoded = TOKENIZER.encode(text)
        return len(encoded.ids)
    except Exception as e:
        print(f"Error counting tokens: {e}")
        return 0


def find_markdown_files(directory: str | Path) -> list[Path]:
    """
    Recursively find all markdown files in a directory.

    Args:
        directory: Path to the directory to search

    Returns:
        List of Path objects for each .md file found
    """
    directory = Path(directory)
    return sorted(directory.rglob("*.md"))


class ParseError(Exception):
    """Raised when a markdown file cannot be parsed."""

    pass


def parse_markdown(file_path: Path) -> tuple[dict, str]:
    """
    Parse a markdown file and extract frontmatter and content.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (metadata dict, content string)

    Raises:
        ParseError: If the file cannot be parsed (e.g., malformed YAML frontmatter)
    """
    try:
        post = frontmatter.load(str(file_path))
        metadata = dict(post.metadata)
        content = post.content
        return metadata, content
    except Exception as e:
        raise ParseError(f"Failed to parse {file_path}: {e}") from e


def chunk_by_tokens(content: str, chunk_size: int = 256, overlap: int = 50) -> list[str]:
    """
    Split content into chunks based on token count using a sliding window.

    Args:
        content: The content to chunk
        chunk_size: Maximum tokens per chunk (default: 256 for all-MiniLM-L6-v2)
        overlap: Number of tokens to overlap between chunks (default: 50)

    Returns:
        List of content chunks, each under chunk_size
    """
    if not TOKENIZER:
        # Fallback: return entire content as one chunk
        return [content.strip()] if content.strip() else []

    if not content.strip():
        return []

    # Create a chunking tokenizer with truncation enabled
    chunking_tokenizer = Tokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    chunking_tokenizer.enable_truncation(max_length=chunk_size, stride=overlap, strategy="longest_first")
    chunking_tokenizer.no_padding()

    # Encode with overflowing tokens
    encoded = chunking_tokenizer.encode(content)

    # Collect all chunks using character offsets from the original text
    # This preserves the original formatting instead of reconstructing from tokens
    chunks = []

    def extract_chunk_text(encoding) -> str:
        """Extract original text using token offsets."""
        offsets = encoding.offsets
        # Filter out special tokens (they have (0, 0) offsets)
        valid_offsets = [(start, end) for start, end in offsets if start != end]
        if not valid_offsets:
            return ""
        start_char = valid_offsets[0][0]
        end_char = valid_offsets[-1][1]
        return content[start_char:end_char].strip()

    # First chunk
    chunk_text = extract_chunk_text(encoded)
    if chunk_text:
        chunks.append(chunk_text)

    # Overflowing chunks
    for overflow_encoding in encoded.overflowing:
        chunk_text = extract_chunk_text(overflow_encoding)
        if chunk_text:
            chunks.append(chunk_text)

    return chunks


# ==================== Chunk File Operations ====================


def clear_chunks_dir(corpus_name: str) -> Path:
    """
    Clear and recreate the chunks directory for a corpus.

    Args:
        corpus_name: Name of the corpus (used as subdirectory name)

    Returns:
        Path to the chunks directory
    """
    chunks_dir = CHUNKS_DIR / corpus_name
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    return chunks_dir


def write_chunk_file(
    chunks_dir: Path,
    file_index: int,
    source_file: str,
    metadata: dict,
    params: dict,
    chunks: list[dict],
) -> Path:
    """
    Write chunk data for a single source file as readable markdown.

    Output format uses YAML frontmatter for metadata and delimiters
    between chunks for easy visual inspection.

    Args:
        chunks_dir: Directory to write chunks to
        file_index: Index for ordering (used in filename)
        source_file: Original source filename
        metadata: Frontmatter metadata from source file
        params: Chunking parameters (chunk_size, overlap)
        chunks: List of chunk dicts with index, token_count, text

    Returns:
        Path to the written chunk file
    """
    file_stem = Path(source_file).stem
    chunk_file = chunks_dir / f"{file_index:02d}_{file_stem}.chunks.md"

    # Build frontmatter
    lines = ["---"]
    lines.append(f'source_file: "{source_file}"')
    lines.append(f"chunk_size: {params.get('chunk_size', 256)}")
    lines.append(f"overlap: {params.get('overlap', 50)}")
    lines.append(f"total_chunks: {len(chunks)}")

    # Add original metadata
    for key, value in metadata.items():
        if isinstance(value, str):
            # Quote strings that might have special chars
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")

    lines.append("---")
    lines.append("")

    # Write each chunk with delimiter
    for chunk in chunks:
        idx = chunk["index"]
        tokens = chunk["token_count"]
        text = chunk["text"]

        lines.append(f"----- chunk {idx} ({tokens} tokens) -----")
        lines.append("")
        lines.append(text)
        lines.append("")

    with open(chunk_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return chunk_file


def write_manifest(
    chunks_dir: Path,
    corpus_name: str,
    source_dir: str,
    params: dict,
    stats: dict,
) -> Path:
    """
    Write manifest file with chunking summary.

    Args:
        chunks_dir: Directory containing chunk files
        corpus_name: Name of the corpus
        source_dir: Path to source directory
        params: Chunking parameters
        stats: Summary statistics (total_files, total_chunks, total_tokens)

    Returns:
        Path to the manifest file
    """
    manifest_file = chunks_dir / "manifest.json"

    data = {
        "corpus_name": corpus_name,
        "source_dir": source_dir,
        "created_at": datetime.now().isoformat(),
        "params": params,
        "summary": stats,
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return manifest_file


def read_manifest(chunks_dir: Path) -> dict | None:
    """
    Read manifest file from chunks directory.

    Args:
        chunks_dir: Directory containing chunk files

    Returns:
        Manifest data dict, or None if not found
    """
    manifest_file = chunks_dir / "manifest.json"
    if not manifest_file.exists():
        return None

    with open(manifest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_chunk_markdown(content: str) -> dict:
    """
    Parse a chunk markdown file into structured data.

    Args:
        content: Raw markdown content with frontmatter and chunk delimiters

    Returns:
        Dict with source_file, metadata, params, total_chunks, chunks
    """
    import re

    # Parse frontmatter
    fm_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(fm_pattern, content, re.DOTALL)

    if not match:
        raise ValueError("Invalid chunk file: missing frontmatter")

    frontmatter_raw = match.group(1)
    body = match.group(2)

    # Parse frontmatter fields
    frontmatter = {}
    for line in frontmatter_raw.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            # Try to convert numbers
            if value.isdigit():
                value = int(value)
            frontmatter[key] = value

    # Extract known fields
    source_file = frontmatter.pop('source_file', '')
    chunk_size = frontmatter.pop('chunk_size', 256)
    overlap = frontmatter.pop('overlap', 50)
    total_chunks = frontmatter.pop('total_chunks', 0)

    # Remaining frontmatter is original metadata
    metadata = frontmatter

    # Parse chunks from body using delimiter pattern
    chunk_pattern = r'----- chunk (\d+) \((\d+) tokens\) -----\n\n(.*?)(?=\n\n----- chunk|\Z)'
    chunk_matches = re.findall(chunk_pattern, body, re.DOTALL)

    chunks = []
    for idx_str, tokens_str, text in chunk_matches:
        chunks.append({
            "index": int(idx_str),
            "token_count": int(tokens_str),
            "text": text.strip(),
        })

    return {
        "source_file": source_file,
        "metadata": metadata,
        "params": {"chunk_size": chunk_size, "overlap": overlap},
        "total_chunks": total_chunks,
        "chunks": chunks,
    }


def read_chunk_files(chunks_dir: Path) -> list[dict]:
    """
    Read all chunk markdown files from a directory.

    Args:
        chunks_dir: Directory containing chunk files

    Returns:
        List of chunk file data dicts, sorted by filename
    """
    chunk_files = sorted(chunks_dir.glob("*.chunks.md"))
    results = []

    for chunk_file in chunk_files:
        with open(chunk_file, "r", encoding="utf-8") as f:
            content = f.read()
        results.append(parse_chunk_markdown(content))

    return results


def ingest_file(
    file_path: Path,
    collection,
    base_dir: Path | None = None,
    chunk_size: int = 256,
    overlap: int = 50,
) -> int:
    """
    Ingest a single markdown file into the collection.

    Args:
        file_path: Path to the markdown file
        collection: ChromaDB collection to add documents to
        base_dir: Base directory for computing relative paths
        chunk_size: Maximum tokens per chunk (default: 256)
        overlap: Number of tokens to overlap between chunks (default: 50)

    Returns:
        Number of chunks added
    """
    try:
        metadata, content = parse_markdown(file_path)
    except ParseError as e:
        print(f"  Skipping {file_path.name}: {e}")
        return 0

    chunks = chunk_by_tokens(content, chunk_size=chunk_size, overlap=overlap)

    if not chunks:
        print(f"  Skipping {file_path.name}: no content")
        return 0

    # Compute relative path for metadata
    if base_dir:
        relative_path = str(file_path.relative_to(base_dir))
    else:
        relative_path = file_path.name

    # Prepare data for batch insertion
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        doc_id = f"{file_path.stem}_{i}"
        ids.append(doc_id)
        documents.append(chunk)

        token_count = count_tokens(chunk)
        print(f"    Chunk {i}: {token_count} tokens")

        # Build metadata for this chunk
        chunk_metadata = {
            "source_file": relative_path,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }

        # Add all frontmatter fields
        for key, value in metadata.items():
            if isinstance(value, list):
                # ChromaDB doesn't support list metadata, so join as comma-separated
                chunk_metadata[key] = ", ".join(str(v) for v in value)
            else:
                # Convert to string to handle dates, numbers, etc.
                chunk_metadata[key] = str(value)

        metadatas.append(chunk_metadata)

    # Add all chunks to the collection
    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    return len(chunks)


def sanitize_collection_name(name: str) -> str:
    """
    Sanitize a string for use as a ChromaDB collection name.

    Converts to lowercase, replaces spaces/underscores with hyphens,
    and removes any characters that aren't alphanumeric or hyphens.

    Args:
        name: The string to sanitize

    Returns:
        Sanitized string safe for collection names
    """
    import re

    # Lowercase and replace spaces/underscores with hyphens
    name = name.lower().replace(" ", "-").replace("_", "-")
    # Keep only alphanumeric and hyphens
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Collapse multiple hyphens
    name = re.sub(r"-+", "-", name)
    # Strip leading/trailing hyphens
    return name.strip("-")


def ingest_directory(
    directory: str | Path,
    collection_name: str | None = None,
    chunk_size: int = 256,
    overlap: int = 50,
) -> dict:
    """
    Ingest all markdown files from a directory into ChromaDB.

    Client configuration is read from environment variables:
        - CHROMA_CLIENT_TYPE: "persistent" (default) or "cloud"
        - CHROMA_PERSIST_PATH: Local storage path (for persistent mode)
        - CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY: Cloud credentials

    Args:
        directory: Path to the directory containing markdown files
        collection_name: Name of the ChromaDB collection (default: auto-generated)
        chunk_size: Maximum tokens per chunk (default: 256)
        overlap: Number of tokens to overlap between chunks (default: 50)

    Returns:
        Dictionary with ingestion statistics
    """
    directory = Path(directory)

    # Generate default collection name if not provided
    if collection_name is None:
        folder_name = sanitize_collection_name(directory.name)
        collection_name = f"{folder_name}-{chunk_size}chunk-{overlap}overlap"

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    # Get the ChromaDB client and collection (config from env vars)
    # create RAG_DB_FILE_PATH if it doesn't exist
    RAG_DB_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = PersistentClient(path=str(RAG_DB_FILE_PATH))
    collection = client.get_or_create_collection(name=collection_name)

    # Find all markdown files
    md_files = find_markdown_files(directory)

    if not md_files:
        print(f"No markdown files found in {directory}")
        return {"files_processed": 0, "chunks_added": 0}

    print(f"Found {len(md_files)} markdown file(s) in {directory}")

    total_chunks = 0
    files_processed = 0

    for file_path in md_files:
        print(f"Processing: {file_path.name}")
        chunks_added = ingest_file(
            file_path,
            collection,
            base_dir=directory,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        total_chunks += chunks_added
        files_processed += 1
        print(f"  Added {chunks_added} chunk(s)")

    total_in_collection = collection.count()

    # Print summary
    print()
    print("=" * 50)
    print("Ingestion Summary")
    print("=" * 50)
    print(f"  Source:        {directory}")
    print(f"  Collection:    {collection_name}")
    print(f"  DB path:       {RAG_DB_FILE_PATH}")
    print(f"  Chunk size:    {chunk_size} tokens")
    print(f"  Overlap:       {overlap} tokens")
    print("-" * 50)
    print(f"  Files:         {files_processed}")
    print(f"  Chunks added:  {total_chunks}")
    print(f"  Total in DB:   {total_in_collection}")
    print("=" * 50)

    return {
        "files_processed": files_processed,
        "chunks_added": total_chunks,
        "collection_name": collection_name,
        "total_in_collection": total_in_collection,
    }


# ==================== Two-Phase Chunking ====================


def create_chunks_to_files(
    directory: str | Path,
    chunk_size: int = 256,
    overlap: int = 50,
) -> dict:
    """
    Create chunk files for inspection without ingesting to ChromaDB.

    This is the "preview" phase of the two-phase chunking workflow.
    Chunks are written to data/chunks/{corpus_name}/ for user inspection.

    Args:
        directory: Path to the directory containing markdown files
        chunk_size: Maximum tokens per chunk (default: 256)
        overlap: Number of tokens to overlap between chunks (default: 50)

    Returns:
        Dictionary with chunking statistics and chunks_dir path
    """
    directory = Path(directory)
    corpus_name = sanitize_collection_name(directory.name)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    # Clear and create chunks directory
    chunks_dir = clear_chunks_dir(corpus_name)

    # Find all markdown files
    md_files = find_markdown_files(directory)

    if not md_files:
        print(f"No markdown files found in {directory}")
        return {"files_processed": 0, "total_chunks": 0, "chunks_dir": str(chunks_dir)}

    print(f"Found {len(md_files)} markdown file(s) in {directory}")
    print()
    print("Creating chunks...")

    params = {"chunk_size": chunk_size, "overlap": overlap}
    total_chunks = 0
    total_tokens = 0
    files_processed = 0

    for file_index, file_path in enumerate(md_files):
        try:
            metadata, content = parse_markdown(file_path)
        except ParseError as e:
            print(f"  Skipping {file_path.name}: {e}")
            continue

        # Create chunks
        text_chunks = chunk_by_tokens(content, chunk_size=chunk_size, overlap=overlap)

        if not text_chunks:
            print(f"  Skipping {file_path.name}: no content")
            continue

        # Build chunk data
        chunks_data = []
        for i, chunk_text in enumerate(text_chunks):
            token_count = count_tokens(chunk_text)
            total_tokens += token_count
            chunks_data.append({
                "index": i,
                "token_count": token_count,
                "text": chunk_text,
            })

        # Write chunk file
        relative_path = str(file_path.relative_to(directory))
        write_chunk_file(chunks_dir, file_index, relative_path, metadata, params, chunks_data)

        total_chunks += len(chunks_data)
        files_processed += 1
        print(f"  {file_path.name} → {len(chunks_data)} chunks")

    # Write manifest
    stats = {
        "total_files": files_processed,
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
    }
    write_manifest(chunks_dir, corpus_name, str(directory), params, stats)

    return {
        "files_processed": files_processed,
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
        "chunks_dir": str(chunks_dir),
        "corpus_name": corpus_name,
    }


def ingest_from_chunks(
    chunks_dir: str | Path,
    collection_name: str | None = None,
) -> dict:
    """
    Ingest pre-created chunks from files into ChromaDB.

    This is the "accept" phase of the two-phase chunking workflow.
    Reads chunks from data/chunks/{corpus_name}/ and ingests to ChromaDB.

    Args:
        chunks_dir: Path to the chunks directory
        collection_name: Name of the ChromaDB collection (default: from manifest)

    Returns:
        Dictionary with ingestion statistics
    """
    chunks_dir = Path(chunks_dir)

    if not chunks_dir.exists():
        raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")

    # Read manifest
    manifest = read_manifest(chunks_dir)
    if not manifest:
        raise ValueError(f"No manifest.json found in {chunks_dir}")

    # Use collection name from manifest or generate one
    if collection_name is None:
        params = manifest["params"]
        corpus_name = manifest["corpus_name"]
        collection_name = f"{corpus_name}-{params['chunk_size']}chunk-{params['overlap']}overlap"

    # Get the ChromaDB client and collection
    RAG_DB_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = PersistentClient(path=str(RAG_DB_FILE_PATH))
    collection = client.get_or_create_collection(name=collection_name)

    # Read all chunk files
    chunk_files = read_chunk_files(chunks_dir)

    if not chunk_files:
        print(f"No chunk files found in {chunks_dir}")
        return {"files_processed": 0, "chunks_added": 0}

    print(f"Ingesting {len(chunk_files)} file(s) to collection '{collection_name}'...")

    total_chunks = 0

    for file_data in chunk_files:
        source_file = file_data["source_file"]
        file_stem = Path(source_file).stem
        metadata = file_data["metadata"]

        ids = []
        documents = []
        metadatas = []

        for chunk in file_data["chunks"]:
            doc_id = f"{file_stem}_{chunk['index']}"
            ids.append(doc_id)
            documents.append(chunk["text"])

            # Build metadata for ChromaDB
            chunk_metadata = {
                "source_file": source_file,
                "chunk_index": chunk["index"],
                "total_chunks": file_data["total_chunks"],
            }
            # Add all frontmatter fields
            for key, value in metadata.items():
                if isinstance(value, list):
                    chunk_metadata[key] = ", ".join(str(v) for v in value)
                else:
                    chunk_metadata[key] = str(value)

            metadatas.append(chunk_metadata)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        total_chunks += len(ids)
        print(f"  {source_file} → {len(ids)} chunks ingested")

    total_in_collection = collection.count()

    # Print summary
    print()
    print("=" * 50)
    print("Ingestion Complete")
    print("=" * 50)
    print(f"  Collection:    {collection_name}")
    print(f"  DB path:       {RAG_DB_FILE_PATH}")
    print("-" * 50)
    print(f"  Files:         {len(chunk_files)}")
    print(f"  Chunks added:  {total_chunks}")
    print(f"  Total in DB:   {total_in_collection}")
    print("=" * 50)

    return {
        "files_processed": len(chunk_files),
        "chunks_added": total_chunks,
        "collection_name": collection_name,
        "total_in_collection": total_in_collection,
    }


def prompt_with_default(prompt: str, default: str) -> str:
    """
    Prompt the user for input with a default value.

    Args:
        prompt: The prompt text to display
        default: The default value shown in brackets

    Returns:
        User input or default if empty
    """
    user_input = input(f"{prompt} [{default}]: ").strip()
    return user_input if user_input else default


def format_file_size(size_bytes: int) -> str:
    """
    Format a file size in bytes to a human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.5 MB" or "256 KB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_directory_stats(directory: Path) -> tuple[int, int]:
    """
    Get stats for a directory: markdown file count and total size.

    Args:
        directory: Path to the directory

    Returns:
        Tuple of (markdown_file_count, total_size_bytes)
    """
    md_files = list(directory.rglob("*.md"))
    total_size = sum(f.stat().st_size for f in md_files)
    return len(md_files), total_size


def get_corpus_directories() -> list[Path]:
    """
    Get list of directories in data/corpus/.

    Returns:
        Sorted list of directory paths
    """
    corpus_dir = Path(__file__).parent.parent / "data" / "corpus"
    if not corpus_dir.exists():
        return []
    return sorted([d for d in corpus_dir.iterdir() if d.is_dir()])


def select_directory() -> Path:
    """
    Prompt user to select a corpus directory.

    Returns:
        Path to the selected directory
    """
    corpus_dirs = get_corpus_directories()

    while True:
        if corpus_dirs:
            print("Available corpus directories:")
            for i, d in enumerate(corpus_dirs, start=1):
                file_count, total_size = get_directory_stats(d)
                size_str = format_file_size(total_size)
                print(f"  [{i}] {d.name:<30} ({file_count} files, {size_str})")
            print(f"  [{len(corpus_dirs) + 1}] Enter a custom path")
            print()

            choice = input("Select directory: ").strip()

            if not choice:
                print("  Error: Selection is required. Try again.\n")
                continue

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(corpus_dirs):
                    return corpus_dirs[choice_num - 1]
                elif choice_num == len(corpus_dirs) + 1:
                    # Fall through to custom path entry
                    pass
                else:
                    print(f"  Error: Please enter a number between 1 and {len(corpus_dirs) + 1}.\n")
                    continue
            except ValueError:
                print("  Error: Please enter a valid number.\n")
                continue

        # Custom path entry (either no corpus dirs or user chose custom)
        directory = input("Directory containing markdown files: ").strip()
        if directory:
            dir_path = Path(directory).expanduser().resolve()
            if dir_path.exists() and dir_path.is_dir():
                return dir_path
            print(f"  Error: '{directory}' is not a valid directory. Try again.\n")
        else:
            if not corpus_dirs:
                print("  Error: Directory is required. Try again.\n")
            else:
                print("  Error: Please enter a path.\n")


def get_chunking_params(defaults: dict | None = None) -> dict:
    """
    Prompt user for chunking parameters.

    Args:
        defaults: Optional dict with default values for chunk_size and overlap

    Returns:
        Dict with chunk_size, overlap
    """
    defaults = defaults or {}
    default_chunk_size = str(defaults.get("chunk_size", 256))
    default_overlap = str(defaults.get("overlap", 50))

    # Chunk size
    while True:
        chunk_size_str = prompt_with_default("Chunk size (tokens)", default_chunk_size)
        try:
            chunk_size = int(chunk_size_str)
            if chunk_size > 0:
                break
            print("  Error: Chunk size must be positive.")
        except ValueError:
            print("  Error: Please enter a valid number.")

    # Overlap
    while True:
        overlap_str = prompt_with_default("Overlap (tokens)", default_overlap)
        try:
            overlap = int(overlap_str)
            if overlap >= 0:
                break
            print("  Error: Overlap cannot be negative.")
        except ValueError:
            print("  Error: Please enter a valid number.")

    return {
        "chunk_size": chunk_size,
        "overlap": overlap,
    }


def interactive_mode() -> dict | None:
    """
    Run two-phase interactive ingestion workflow.

    Phase 1: Create chunks to files for inspection
    Phase 2: User reviews and accepts or re-runs with different parameters

    Returns:
        Dictionary with ingestion results, or None if user quit
    """
    print("=" * 50)
    print("Markdown Ingestion - Interactive Mode")
    print("=" * 50)
    print("Press Enter to accept default values.\n")

    # Step 1: Select directory (only done once)
    dir_path = select_directory()
    print()

    # Loop for chunking params (user can re-run with different params)
    chunking_defaults = None

    while True:
        # Step 2: Get chunking parameters
        params = get_chunking_params(chunking_defaults)
        print()

        # Step 3: Create chunks to files
        result = create_chunks_to_files(
            dir_path,
            chunk_size=params["chunk_size"],
            overlap=params["overlap"],
        )

        # Step 4: Show summary
        print()
        print("=" * 50)
        print("Chunk Preview Summary")
        print("=" * 50)
        print(f"  Files processed:  {result['files_processed']}")
        print(f"  Total chunks:     {result['total_chunks']}")
        if result['total_chunks'] > 0:
            avg_tokens = result['total_tokens'] // result['total_chunks']
            print(f"  Avg tokens/chunk: {avg_tokens}")
        print()
        print(f"  Chunks written to: {result['chunks_dir']}")
        print()

        # Step 5: User decision
        print("[A] Accept and ingest to ChromaDB")
        print("[R] Re-run chunking with different parameters")
        print("[Q] Quit (chunks preserved for later)")
        print()

        while True:
            choice = input("Choice: ").strip().upper()
            if choice in ("A", "R", "Q"):
                break
            print("  Please enter A, R, or Q.")

        if choice == "Q":
            print("\nChunks preserved. Run again to resume or modify.")
            return None

        if choice == "A":
            # Step 6: Ingest to ChromaDB
            print()

            # Ask for collection name
            corpus_name = result["corpus_name"]
            default_collection = f"{corpus_name}-{params['chunk_size']}chunk-{params['overlap']}overlap"
            collection_name = prompt_with_default("Collection name", default_collection)
            print()

            return ingest_from_chunks(result["chunks_dir"], collection_name=collection_name)

        # choice == "R": Re-run with different params
        print("\n" + "=" * 50)
        print("Re-running chunking with new parameters...")
        print("=" * 50 + "\n")
        chunking_defaults = params  # Use previous values as defaults


def main():
    """CLI entry point for ingestion."""
    # If no arguments provided, run interactive mode
    if len(sys.argv) == 1:
        try:
            result = interactive_mode()
            if result is None:
                # User quit without ingesting
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        return

    # Otherwise, use argument parser
    parser = argparse.ArgumentParser(
        description="Ingest markdown files into ChromaDB. Run without arguments for interactive mode."
    )
    parser.add_argument("directory", help="Directory containing markdown files")
    parser.add_argument(
        "collection_name",
        nargs="?",
        default=None,
        help="ChromaDB collection name (default: {folder}-{chunk_size}chunk-{overlap}overlap)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=256,
        help="Maximum tokens per chunk (default: 256)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Token overlap between chunks (default: 50)",
    )

    args = parser.parse_args()

    try:
        ingest_directory(
            args.directory,
            collection_name=args.collection_name,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
