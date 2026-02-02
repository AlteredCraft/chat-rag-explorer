# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This app is for educational purposes, demonstrating how to build a streamingchat interface with LLMs using Flask and vanilla JavaScript.

All python files should be well documented with file headers and function docstrings.

Keep code modular and organized following Flask best practices (Blueprints, Application Factory pattern). 
**IMPORTANT**: Don't be clever, readable code is a MUST.

## Running the Application

```bash
# Start the dev server (auto-finds available port 8000-8004)
uv run main.py
```

The app runs at http://127.0.0.1:8000 by default.

## Testing

```bash
uv run pytest                     # Run all tests (randomized order)
uv run pytest tests/unit/         # Run only unit tests
uv run pytest -v                  # Verbose output
uv run pytest -x                  # Stop on first failure
uv run pytest --cov               # Run with coverage report
uv run pytest -k "test_name"      # Run specific test by name
```

**IMPORTANT:** 
- After implementing new features or bug fixes, ALWAYS run the full test suite to ensure nothing is broken.
- Code coverage is a good indicator but don't create 'Mock Fests' just to boost coverage numbers. Review low cov code for valueable tests and/or refactor opportunities to improve testability.
- Our priority is to test our business logic, not external libraries or frameworks.

**Test Policy**
- Unit tests live in `tests/unit/`, organized to mirror `chat_rag_explorer/`
- Unit tests must not make network calls - mock external dependencies
- Use `tmp_path` fixture for any file operations
- Use fixtures in `conftest.py` for shared test setup (Flask app, test client)
- Tests run in random order to catch hidden state dependencies

## Dependencies

Use `uv` for all dependency management:
```bash
uv add <package>      # Add dependency
uv remove <package>   # Remove dependency
```

Do not edit pyproject.toml directly for dependencies.

## Architecture

**Flask Application Factory Pattern**
- `main.py` - Entry point, handles port discovery and startup
- `chat_rag_explorer/__init__.py` - `create_app()` factory function
- `config.py` - Environment configuration loaded from `.env`

**Backend Services (Singleton Pattern)**
- `services.py` - `chat_service`: OpenRouter LLM streaming via OpenAI SDK
- `rag_config_service.py` - `rag_config_service`: ChromaDB connection management (local/server/cloud modes)
- `prompt_service.py` - `prompt_service`: System prompt CRUD operations
- `chat_history_service.py` - `chat_history_service`: Conversation logging to JSONL

**API Design**
- All endpoints use request_id for log correlation
- Streaming responses use SSE with `__METADATA__:` prefix for token usage
- Routes defined in `routes.py` as single Blueprint (`main_bp`)

**Frontend**
- Vanilla JS (no framework)
- `static/script.js` - Main chat interface
- `static/settings.js` - Settings page (model picker, prompts, RAG config)
- Uses Marked.js + DOMPurify for markdown rendering (bundled locally)

**Configuration Storage**
- User settings stored in localStorage (model selection, prompts, tabs)
- RAG config persisted to `rag_config.json` in project root
- Prompts stored in `prompts/` directory as markdown files

## Key Patterns

**Request Logging**: All API handlers generate 8-char request IDs and log timing:
```python
request_id = generate_request_id()
logger.info(f"[{request_id}] POST /api/chat - Model: {model}")
```

**ChromaDB Modes**: RAG service supports three connection types:
- `local`: PersistentClient with local directory path
- `server`: HttpClient to ChromaDB server
- `cloud`: CloudClient with tenant/database/API key

**Sample Database Setup**: On startup, `main.py` copies `data/chroma_db_sample/` to `data/chroma_db/` (gitignored) if the destination doesn't exist. This prevents git deltas from ChromaDB's internal file mutations during read operations. The pristine sample remains in `chroma_db_sample/` as the source of truth.

## Changelog

**IMPORTANT**: When committing changes, update `CHANGELOG.txt` with a summary of what was added, changed, or fixed. Group related changes under `[Unreleased]` until a version is released.
