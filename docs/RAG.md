# RAG Integration

This document describes the current state of ChromaDB/RAG integration in Chat RAG Explorer.

## Current Status: Configuration Only

The RAG integration is currently at the **configuration phase**. Users can:
- Connect to ChromaDB databases (local, server, or cloud)
- Browse available collections
- Preview sample records from collections

**Not yet implemented**: Actual RAG query integration to inject relevant context into chat messages.

## Architecture

### Backend Service

**`chat_rag_explorer/rag_config_service.py`** - Singleton service (`rag_config_service`)

Manages ChromaDB connections in three modes:

| Mode | Client | Use Case |
|------|--------|----------|
| `local` | `chromadb.PersistentClient(path=...)` | Direct file-based storage |
| `server` | `chromadb.HttpClient(host, port)` | Local ChromaDB server |
| `cloud` | `chromadb.CloudClient(tenant, database, api_key)` | ChromaDB Cloud service |

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
  "collection": "selected_collection_name"
}
```

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

### Frontend

**`chat_rag_explorer/static/settings.js`** - RAG Settings section (lines 575-1004)

The Settings page (`/settings`) has a "RAG Settings" tab that provides:

1. **Mode Selection** - Radio buttons for local/server/cloud
2. **Mode-specific Configuration**:
   - Local: Path input with validation
   - Server: Host and port inputs
   - Cloud: Tenant ID, database name, API key status display
3. **Test Connection** - Validates config and retrieves collection list
4. **Collection Selector** - Dropdown populated after successful connection
5. **Sample Records** - Preview button to fetch and display sample documents

## User Flow

1. Navigate to Settings > RAG Settings tab
2. Select connection mode (local/server/cloud)
3. Enter connection details
4. Click "Test Connection"
5. If successful, select a collection from dropdown
6. Optionally click "Sample" to preview records
7. Click "Save Settings" to persist configuration

## Local Path Validation

For local mode, the service validates:
- Path exists
- Path is a directory
- Directory contains `chroma.sqlite3` (ChromaDB marker file)

## Next Steps (Not Implemented)

To complete RAG integration:

1. **Query Service** - Add method to query collection for relevant documents based on user message
2. **Context Injection** - Modify chat flow to:
   - Query ChromaDB with user's message
   - Format retrieved documents as context
   - Prepend context to system prompt or inject as additional message
3. **UI Feedback** - Show which documents were retrieved for each response
