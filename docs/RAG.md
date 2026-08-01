# RAG Integration

How the ChromaDB/RAG integration works in RAG Lab — the reference companion to the [README](../README.md).

## The idea in one paragraph

A language model only knows what was in its training data plus what you put in the prompt. RAG is the second half of that: before calling the model, search your own documents for passages relevant to the question, then paste those passages into the prompt alongside it. The model isn't "learning" your documents — it's reading them, once, at question time. Everything below is machinery in service of that one move.

The search step works on **embeddings**: each chunk of text is converted to a vector of numbers positioned so that similar meanings land near each other. Your question becomes a vector too, and retrieval returns the chunks nearest to it. "Nearest" is measured as **distance**, where lower means more similar — which is why a distance threshold is a quality filter. New to this? [Embeddings primer](https://developers.google.com/machine-learning/crash-course/embeddings) · [Chroma docs](https://docs.trychroma.com/).

What the app gives you on top of that: connect to ChromaDB (local, server, or cloud), browse collections, tune retrieval settings, toggle RAG per conversation, and inspect exactly which documents were retrieved for any response.

## Architecture

### Backend Services

**`chat_rag_explorer/rag_config_service.py`** - Singleton service (`rag_config_service`)

Manages ChromaDB connections in three modes:

| Mode | Client | Use Case |
|------|--------|----------|
| `local` | `chromadb.PersistentClient(path=...)` | Direct file-based storage |
| `server` | `chromadb.HttpClient(host, port)` | Local ChromaDB server |
| `cloud` | `chromadb.CloudClient(tenant, database, api_key)` | ChromaDB Cloud service |

Key methods:
- `get_client()` - Returns configured ChromaDB client
- `list_collections()` - Lists available collections
- `query_collection(query_text, n_results, distance_threshold)` - Queries for relevant documents
- `get_sample_records(collection, limit)` - Fetches sample documents for preview

**`chat_rag_explorer/routes.py`** - Chat integration

The `/api/chat` endpoint handles RAG integration:
1. If `rag_enabled=true`, queries ChromaDB with the user's message
2. Augments the user message with retrieved context using XML format
3. Includes RAG metadata in the response for UI display

### Context Injection Format

When RAG retrieves documents, the user message is augmented with XML-formatted context:

```xml
<knowledge_base_context>
<document index="1">First retrieved document content...</document>
<document index="2">Second retrieved document content...</document>
</knowledge_base_context>

<original_user_message>
What is the user's original question?
</original_user_message>
```

This format:
- Clearly separates context from the user's question
- Uses indexed documents for clarity
- Is visible in the "View Details" modal for transparency

### Configuration Storage

**`rag_config.json`** - Project root

```json
{
  "mode": "local",
  "local_path": "/path/to/chromadb",
  "server_host": "localhost",
  "server_port": 8000,
  "cloud_tenant": "",
  "cloud_database": "",
  "collection": "selected_collection_name",
  "n_results": 5,
  "distance_threshold": null
}
```

| Field | Description |
|-------|-------------|
| `mode` | Connection mode: `local`, `server`, or `cloud` |
| `collection` | Selected collection name for queries |
| `n_results` | Number of documents to retrieve (1-10) |
| `distance_threshold` | Max distance for results (`null` = no filtering) |

For cloud mode, the API key is read from environment variable `CHROMADB_API_KEY` (not stored in config).

### API Endpoints

All endpoints defined in `chat_rag_explorer/routes.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rag/config` | GET | Get current RAG configuration |
| `/api/rag/config` | POST | Save RAG configuration |
| `/api/rag/validate-path` | POST | Validate local ChromaDB path exists |
| `/api/rag/test-connection` | POST | Test connection, returns collection list |
| `/api/rag/api-key-status` | GET | Check if `CHROMADB_API_KEY` is configured |
| `/api/rag/discover-databases` | GET | Scan `./data/*` for ChromaDB directories (skips `chroma_db_sample`) |
| `/api/rag/sample` | POST | Fetch sample records from a collection |

## Frontend

### Settings Page

**`chat_rag_explorer/static/settings.js`** - RAG Settings tab

The Settings page (`/settings#rag`) provides a wizard-style interface:

1. **Step 1: Configure** - Select mode and enter connection details
   - Local: a dropdown of databases discovered under `./data/`, with a "Switch to manual entry" toggle for a path anywhere else
   - Server: Host and port inputs
   - Cloud: Tenant ID, database name, API key status

2. **Step 2: Test Connection** - Validates config and retrieves the collection list. This is the only thing that refreshes that list, so click it again after ingesting new content.

3. **Step 3: Select Collection** - Choose collection + configure retrieval settings
   - Results Count slider (1-10)
   - Distance Threshold slider (0 = off, up to 3.0)

4. **Step 4: Save** - Persists configuration to `rag_config.json`

### Chat Interface

**`chat_rag_explorer/static/script.js`** - RAG toggle and display

The chat page includes:

- **RAG Toggle** - Enable/disable RAG in the sidebar (links to settings if not configured)
- **Context Badge** - Shows "Retrieved X document(s) from collection_name" above responses
- **View Details Modal** - Shows the full augmented message sent to the LLM, including all retrieved documents

## User Flow

### Initial Setup

1. Navigate to Settings > RAG Settings tab (or click "RAG" link in chat sidebar)
2. Select connection mode (local/server/cloud)
3. Choose a discovered database, or enter connection details
4. Click "Test Connection"
5. Select a collection from dropdown
6. Adjust retrieval settings (optional)
7. Click "Save Settings"

### Using RAG in Chat

1. Enable the RAG toggle in the sidebar
2. Send a message - the system will:
   - Query ChromaDB for relevant documents
   - Inject context into your message
   - Send augmented message to the LLM
3. See the badge showing how many documents were retrieved
4. Click "view details" to see exactly what was sent to the LLM

## Local Path Validation

For local mode, the service validates:
- Path exists
- Path is a directory
- Directory contains `chroma.sqlite3` (ChromaDB marker file)

## Sample Data

A pre-built ChromaDB with 429 chunks from "The Morn Chronicles" (a Star Trek DS9 fan fiction, 28 chapters) is included in the repository, in the collection `morn-chronicles-256chunk-50overlap`. On first startup, the app automatically copies the pristine sample from `data/chroma_db_sample/` to `data/chroma_db/` (which is gitignored) to prevent git deltas from ChromaDB's internal file mutations.

That is the only *pre-built* collection, but not the only corpus available. `data/corpus/` holds seven markdown data sets ready to ingest — the README's [Try another corpus](../README.md#try-another-corpus) lists them and walks through enabling one.

> **Point the app at `data/chroma_db`, never at `data/chroma_db_sample`.** ChromaDB writes to `chroma.sqlite3` even when it is only reading, so querying the sample directly dirties files that are committed to the repo. That is the whole reason the working copy exists.

To use it:

1. Go to Settings > RAG Settings
2. Select "Local" mode
3. Pick `chroma_db` from the discovered-database dropdown (or switch to manual entry and type a path)
4. Test connection and select the collection
5. Save and enable RAG in chat

## Loading Your Own Documents

The sample collection has no privileged status. `data/chroma_db` is a plain ChromaDB directory, and `utils/ingest.py` writes into that same directory — so any new data set becomes a new *collection* sitting alongside `morn-chronicles-256chunk-50overlap`, selectable from the same dropdown. Nothing is replaced, and switching between them costs one dropdown change and a save.

If you only want to try a different data set, the repo already ships seven corpora in `data/corpus/` and step 2 below is all you need — see [Try another corpus](../README.md#try-another-corpus) in the README. This section is for bringing in documents of your own.

See [utils/README.md](../utils/README.md) for the full CLI reference.

### 1. Stage the markdown

Source documents live in `data/corpus/<name>/`, one directory per corpus. `find_markdown_files()` walks it recursively and skips any file whose name begins with `_` — that's how `morn_chronicles` keeps `_canon_bible.md` and `_chapter_outlines.md` next to the chapters without ingesting them.

Only markdown is read. A single large file should be split first:

```bash
uv run utils/split.py "My Book.md" --out data/corpus/my_book --pattern "##"
```

`split.py` defaults its output to `data/<name>/`, **not** `data/corpus/<name>/`. Since `get_corpus_directories()` only lists `data/corpus/*`, output written to the default lands somewhere the ingest picker won't show. Pass `--out` and the problem disappears.

YAML frontmatter is preserved. `split.py` emits `section_number` and `section_title`, plus anything you add with `--fm`, and every one of those fields is copied onto every chunk as ChromaDB metadata — which is what makes source attribution possible in the "view details" modal.

### 2. Chunk, inspect, then commit

```bash
uv run utils/ingest.py
```

Interactive mode is two-phase by design. `create_chunks_to_files()` writes previews to `data/chunks/<corpus>/` (gitignored) and stops before touching the database:

```
data/chunks/my-book/
├── manifest.json              # corpus name, source dir, params, totals
├── 00_01_chapter_one.chunks.md
└── 01_02_chapter_two.chunks.md
```

Each `.chunks.md` file is readable markdown — frontmatter with the parameters used, then every chunk with its token count. Read some. The `[R]` option re-chunks with different parameters, `[A]` calls `ingest_from_chunks()` to write them, `[Q]` leaves the previews in place.

This inspect-before-you-commit loop is the tool's reason for existing. Chunk boundaries are the single most consequential decision in a RAG pipeline and the easiest one to get wrong invisibly — chunks that split a definition from its term, or a question from its answer, retrieve badly in ways no error message will ever tell you about.

### 3. Understand the collection name

`[A]` prompts for a collection name, defaulting to `{corpus}-{chunk_size}chunk-{overlap}overlap`. Parameters in the name are a deliberate convenience: ingest the same corpus twice with different settings and you get two collections that can be compared head to head on identical questions.

ChromaDB constrains the name to 3–512 characters from `[a-zA-Z0-9._-]`, starting and ending alphanumeric. `sanitize_collection_name()` handles case and separators but does not enforce the length floor, so a very short corpus directory name can produce a name ChromaDB rejects.

### 4. Wire it up

Return to **Settings → RAG Settings** and click **Test Connection** again. `test_connection()` is what re-lists collections; the dropdown does not poll. Select the new collection, save, and enable RAG in chat.

### Re-ingestion overwrites nothing

`ingest_from_chunks()` builds each chunk ID as `{file_stem}_{chunk_index}` and calls `collection.add()`. ChromaDB silently ignores an `add` for an ID that already exists — no error, no warning, and the **previously stored text is kept**.

The consequence: editing your source documents and re-running with the same parameters produces the same collection name and the same IDs, so the collection still serves the old content. The run reports success and appears to have done nothing.

Ingest under a new collection name whenever the sources change. To reclaim the space, drop the stale one:

```python
import chromadb

client = chromadb.PersistentClient(path="data/chroma_db")
client.delete_collection("my-book-256chunk-50overlap")
```

### Deleting the working database

`data/chroma_db` is gitignored, and `setup_sample_database()` in `main.py` only re-copies the sample when `data/chroma_db/chroma.sqlite3` is absent. Deleting the directory therefore restores the sample on next startup — and permanently discards every collection you ingested. The pristine sample in `data/chroma_db_sample/` is unaffected either way.

---

# Appendix: Deep Dive

## ChromaDB Data Layout

Understanding how ChromaDB stores data helps explain why multiple collections can coexist in a single database path.

### PersistentClient Directory Structure

When you use `chromadb.PersistentClient(path="data/chroma_db")`, ChromaDB creates this structure:

```
data/chroma_db/
├── chroma.sqlite3                          # Shared metadata database
├── 2a31d927-ff2a-4dbf-b30f-094e5e91b702/  # Collection 1 vector data
│   ├── data_level0.bin
│   ├── header.bin
│   ├── length.bin
│   └── link_lists.bin
└── fbe357dd-b35e-4646-86c2-f71862b696f9/  # Collection 2 vector data
    ├── data_level0.bin
    ├── header.bin
    ├── length.bin
    └── link_lists.bin
```

### What Each Component Does

| Component | Purpose |
|-----------|---------|
| `chroma.sqlite3` | SQLite database storing collection metadata, document IDs, and text content for ALL collections in this path |
| UUID directories | HNSW index files for vector similarity search, one directory per collection |
| `data_level0.bin` | The actual vector embeddings |
| `header.bin`, `length.bin`, `link_lists.bin` | HNSW graph structure for fast approximate nearest neighbor search |

### Key Insight: Shared Database

The `chroma.sqlite3` file is **shared across all collections** in that path. This means:

1. **Sample DB + Ingested Data Coexist**: When the app copies the sample database on startup, it brings its `chroma.sqlite3` and collection folder. When you run `utils/ingest.py`, it opens the same `chroma.sqlite3` and adds new collections alongside the existing ones.

2. **Single Connection Point**: The app only needs one path (`data/chroma_db`) to access all collections - both the sample "Morn Chronicles" and any documents you ingest.

3. **Why We Copy the Sample**: ChromaDB mutates `chroma.sqlite3` even during read operations (for internal bookkeeping). By copying `data/chroma_db_sample/` to `data/chroma_db/` on startup, we keep the committed sample pristine while allowing the working copy to be modified freely.

### How Ingestion Works

`utils/ingest.py` hard-codes its destination — there is no environment variable or CLI flag for it:

```python
RAG_DB_FILE_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
# ...
client = PersistentClient(path=str(RAG_DB_FILE_PATH))
collection = client.get_or_create_collection(name=collection_name)
```

This creates or opens `data/chroma_db/chroma.sqlite3` and adds the new collection. The collection name follows the pattern `{corpus}-{chunk_size}chunk-{overlap}overlap` (e.g., `morn-chronicles-256chunk-50overlap`). To build a database somewhere else, copy the directory afterwards and point the app at it via manual path entry.

### Listing All Collections

To see all collections in a database:

```python
import chromadb

client = chromadb.PersistentClient(path="data/chroma_db")
for col in client.list_collections():
    print(f"{col.name}: {col.count()} documents")
```

Or use the RAG Settings UI - after testing the connection, the collection dropdown shows all available collections.
