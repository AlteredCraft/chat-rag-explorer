# RAG Integration

This document describes the ChromaDB/RAG integration in Chat RAG Explorer.

## Current Status: Complete

The RAG integration is fully implemented. Users can:
- Connect to ChromaDB databases (local, server, or cloud)
- Browse and select collections
- Configure retrieval settings (results count, distance threshold)
- Toggle RAG on/off in the chat interface
- See which documents were retrieved for each response

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
| `/api/rag/sample` | POST | Fetch sample records from a collection |

## Frontend

### Settings Page

**`chat_rag_explorer/static/settings.js`** - RAG Settings tab

The Settings page (`/settings#rag`) provides a wizard-style interface:

1. **Step 1: Configure** - Select mode and enter connection details
   - Local: Path input with validation
   - Server: Host and port inputs
   - Cloud: Tenant ID, database name, API key status

2. **Step 2: Test Connection** - Validates config and retrieves collection list

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
3. Enter connection details
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

A pre-built ChromaDB with ~2,000 chunks from the D&D SRD 5.2 ships at `data/chroma_db_sample/`. To use it:

1. Go to Settings > RAG Settings
2. Select "Local" mode
3. Enter path: `data/chroma_db_sample` (relative paths work)
4. Test connection and select the collection
5. Save and enable RAG in chat
