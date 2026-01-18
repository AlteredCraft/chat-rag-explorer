"""Markdown ingestion module for ChromaDB RAG system."""

import argparse
import sys
from pathlib import Path

from chromadb import PersistentClient
import frontmatter


from tokenizers import Tokenizer

RAG_DB_FILE_PATH = Path(__file__).parent.parent / "data" / "chroma_db"

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



def ingest_file(
    file_path: Path,
    collection,
    base_dir: Path | None = None,
    no_chunk: bool = False,
    chunk_size: int = 256,
    overlap: int = 50,
) -> int:
    """
    Ingest a single markdown file into the collection.

    Args:
        file_path: Path to the markdown file
        collection: ChromaDB collection to add documents to
        base_dir: Base directory for computing relative paths
        no_chunk: If True, ingest entire document as single chunk
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

    if no_chunk:
        chunks = [content.strip()] if content.strip() else []
    else:
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
    no_chunk: bool = False,
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
        no_chunk: If True, ingest entire documents without chunking
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
            no_chunk=no_chunk,
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


def main():
    """CLI entry point for ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest markdown files into ChromaDB"
    )
    parser.add_argument("directory", help="Directory containing markdown files")
    parser.add_argument(
        "collection_name",
        nargs="?",
        default=None,
        help="ChromaDB collection name (default: {folder}-{chunk_size}chunk-{overlap}overlap)",
    )
    parser.add_argument(
        "--no-chunk",
        action="store_true",
        help="Ingest entire documents without chunking",
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
            no_chunk=args.no_chunk,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
