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


def parse_markdown(file_path: Path) -> tuple[dict, str]:
    """
    Parse a markdown file and extract frontmatter and content.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (metadata dict, content string)
    """
    post = frontmatter.load(str(file_path))
    metadata = dict(post.metadata)
    content = post.content
    return metadata, content


def chunk_by_tokens(content: str, max_tokens: int = 256, stride: int = 50) -> list[str]:
    """
    Split content into chunks based on token count using a sliding window.

    Args:
        content: The content to chunk
        max_tokens: Maximum tokens per chunk (default: 256 for all-MiniLM-L6-v2)
        stride: Number of tokens to overlap between chunks (default: 50)

    Returns:
        List of content chunks, each under max_tokens
    """
    if not TOKENIZER:
        # Fallback: return entire content as one chunk
        return [content.strip()] if content.strip() else []

    if not content.strip():
        return []

    # Create a chunking tokenizer with truncation enabled
    chunking_tokenizer = Tokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    chunking_tokenizer.enable_truncation(max_length=max_tokens, stride=stride, strategy="longest_first")
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
) -> int:
    """
    Ingest a single markdown file into the collection.

    Args:
        file_path: Path to the markdown file
        collection: ChromaDB collection to add documents to
        base_dir: Base directory for computing relative paths
        no_chunk: If True, ingest entire document as single chunk

    Returns:
        Number of chunks added
    """
    metadata, content = parse_markdown(file_path)

    if no_chunk:
        chunks = [content.strip()] if content.strip() else []
    else:
        chunks = chunk_by_tokens(content)

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


def ingest_directory(
    directory: str | Path,
    collection_name: str = "blog_posts",
    no_chunk: bool = False,
) -> dict:
    """
    Ingest all markdown files from a directory into ChromaDB.

    Client configuration is read from environment variables:
        - CHROMA_CLIENT_TYPE: "persistent" (default) or "cloud"
        - CHROMA_PERSIST_PATH: Local storage path (for persistent mode)
        - CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY: Cloud credentials

    Args:
        directory: Path to the directory containing markdown files
        collection_name: Name of the ChromaDB collection to use
        no_chunk: If True, ingest entire documents without chunking

    Returns:
        Dictionary with ingestion statistics
    """
    directory = Path(directory)

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
            file_path, collection, base_dir=directory, no_chunk=no_chunk
        )
        total_chunks += chunks_added
        files_processed += 1
        print(f"  Added {chunks_added} chunk(s)")

    print(f"\nIngestion complete!")
    print(f"  Files processed: {files_processed}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Collection: {collection_name}")
    print(f"  Total documents in collection: {collection.count()}")

    return {
        "files_processed": files_processed,
        "chunks_added": total_chunks,
        "collection_name": collection_name,
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
        default="blog_posts",
        help="ChromaDB collection name (default: blog_posts)",
    )
    parser.add_argument(
        "--no-chunk",
        action="store_true",
        help="Ingest entire documents without chunking",
    )

    args = parser.parse_args()

    try:
        ingest_directory(
            args.directory,
            collection_name=args.collection_name,
            no_chunk=args.no_chunk,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
