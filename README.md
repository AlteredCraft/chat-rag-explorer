# RAG Lab

[![Tests](https://github.com/AlteredCraft/chat-rag-explorer/actions/workflows/test.yml/badge.svg)](https://github.com/AlteredCraft/chat-rag-explorer/actions/workflows/test.yml)
[![GitHub Release](https://img.shields.io/github/v/release/AlteredCraft/chat-rag-explorer?filter=chat-rag-explorer-*)](https://github.com/AlteredCraft/chat-rag-explorer/releases)

A working chat application you can read end to end. It demonstrates two things that are hard to learn from articles alone: how a **streaming** LLM chat interface actually works, and how **Retrieval-Augmented Generation (RAG)** injects your own documents into a model's context.

The stack is deliberately small so the interesting parts stay visible — **Flask** on the backend, **vanilla JavaScript** on the frontend (no build step, no framework), **OpenRouter** for model access, and **ChromaDB** as the vector store.

The most useful feature for learning is **Inspect Request Details**. Click "view details" on any message to see exactly what the model received — the full augmented prompt, the retrieved documents with their similarity scores, token counts, and timing. Most of RAG's behavior becomes obvious once you can see this.

![Inspect button on chat message](docs/img/inspect-chat-button.png)
![Request details modal](docs/img/inspect-chat-details.png)

> Interested in a RAG workshop for your team? Contact [info@alteredcraft.com](mailto:info@alteredcraft.com), or see [past workshop deliveries](https://lu.ma/altered-craft-workshops?k=c&period=past). Attending a workshop? Start with [docs/PREWORK.md](docs/PREWORK.md) instead.

## Before you start

| You need | Notes |
|----------|-------|
| [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) | To clone the repo. No Git? [Download the ZIP](https://github.com/AlteredCraft/chat-rag-explorer/archive/refs/heads/main.zip) instead. |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Installs Python and every dependency for you. You do **not** need Python installed first. |
| An [OpenRouter API key](https://openrouter.ai/keys) | One key reaches many models. See [cost](#what-this-costs) below. |

You should be comfortable running commands in a terminal. If that's new, start here: [macOS](https://support.apple.com/guide/terminal/welcome/mac) · [Windows](https://learn.microsoft.com/en-us/windows/terminal/) · [Linux](https://documentation.ubuntu.com/desktop/en/latest/tutorial/the-linux-command-line-for-beginners/).

## Get it running

Five steps, start to finish.

**1. Clone the repo and install dependencies**

```bash
git clone https://github.com/AlteredCraft/chat-rag-explorer.git
cd chat-rag-explorer
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, installs the correct Python version, and builds an isolated environment in `.venv/`. Nothing is installed system-wide.

**2. Confirm the install worked**

```bash
uv run pytest
```

You should see all tests pass. These run entirely offline — no API key and no network needed — so this is a clean check that your environment is sound before any credentials enter the picture.

**3. Add your API key**

```bash
cp .env.example .env
```

Open `.env` and set your key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

`.env` is gitignored, so your key will not be committed. Every other setting in that file is optional and already has a sensible default.

`.env` is read once at startup, so if the app is already running, stop it with `Ctrl+C` and start it again before your key takes effect.

**4. Start the app**

```bash
uv run main.py
```

Leave this running — it's your server. `Ctrl+C` in that terminal stops it.

**5. Open it**

Go to the URL printed in your terminal — [http://127.0.0.1:8000](http://127.0.0.1:8000) unless port 8000 was busy. Type a message and send it; the reply should stream in a word at a time.

You don't need to visit Settings first. A model is already selected for you (see [Model Selection](#model-selection)), so a working key is the only thing standing between a fresh clone and a reply.

To confirm the key is genuinely working, watch that first reply arrive. The model dropdown populating is *not* evidence — OpenRouter's catalog is public, so the picker fills in even with a bad key, and the failure only shows up when you actually send a message.

> The app also starts fine *without* a key and says so in the UI, so you can look around before step 3 if you'd rather.

## Try RAG with the included sample data

The repo ships with a pre-built vector database so you can see retrieval working immediately, without preparing any documents. It holds **429 chunks** drawn from 28 chapters of *The Morn Chronicles*, a Star Trek DS9 fan fiction. Deliberately obscure source material — the model has certainly never seen it, so anything it answers correctly had to come from retrieval rather than memory.

1. Go to **Settings → RAG Settings**
2. Choose **Local** mode and enter the path `data/chroma_db`
3. Click **Test Connection**, then select the `morn-chronicles-256chunk-50overlap` collection
4. **Save Settings**, return to chat, and switch on the **RAG** toggle in the sidebar
5. Ask something only the source would know, such as *"How did Morn get his stool at Quark's bar?"*

Now click **view details** on the answer. You'll see the retrieved chunks, their similarity scores, and the fully assembled prompt. Toggle RAG off and ask the same question again — the difference is the entire point of the exercise.

Once that works, try a question the corpus *can't* answer and watch the similarity scores get worse. Retrieval always returns its best matches, even when the best available match is bad, and recognizing that failure mode is most of what separates a working RAG system from a confidently wrong one.

> **First query is slow.** ChromaDB downloads its embedding model (~79 MB) the first time it embeds anything, then caches it in `~/.cache/chroma`. One-time delay; later queries are fast.

Full details in [docs/RAG.md](docs/RAG.md).

## New to these ideas?

You don't need any of this up front — the app runs without it. Reach for these when you hit something you want to understand properly.

| Concept | Where it shows up | Start here |
|---------|-------------------|------------|
| Virtual environments | `uv sync`, the `.venv/` directory | [Python venv tutorial](https://docs.python.org/3/tutorial/venv.html) |
| Flask, routes, blueprints | `chat_rag_explorer/routes.py` | [Flask quickstart](https://flask.palletsprojects.com/en/stable/quickstart/) |
| Server-Sent Events (SSE) | How responses stream in token by token | [MDN: Using SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) |
| Tokens and context windows | The metrics sidebar, token counts | [OpenRouter docs](https://openrouter.ai/docs) |
| Embeddings | Turning text into vectors for search | [Google ML Crash Course](https://developers.google.com/machine-learning/crash-course/embeddings) |
| Vector databases | ChromaDB, collections, similarity | [Chroma docs](https://docs.trychroma.com/) |
| RAG as a pattern | The whole point of the app | [What is RAG?](https://aws.amazon.com/what-is/retrieval-augmented-generation/) · [docs/RAG.md](docs/RAG.md) |
| Chunking and overlap | `utils/ingest.py` parameters | [utils/README.md](utils/README.md) |
| pytest | `tests/` | [pytest getting started](https://docs.pytest.org/en/stable/getting-started.html) |

## What this costs

OpenRouter is pay-as-you-go, and you are billed per token by whichever model you select. Ordinary experimentation with this app runs to cents, not dollars, but it is not free by default.

Two things worth doing if you're watching your budget. Set a [spending limit](https://openrouter.ai/settings/credits) on your account. And note that OpenRouter offers [free models](https://openrouter.ai/models?max_price=0) — though they won't appear in the picker until you add their IDs to `.models_list`, since that file ships with a curated paid set (see [Model Selection](#model-selection)).

## Platform support

Developed and manually tested on **macOS** — that's the best-supported path and the one to prefer if you have the choice.

Automated tests run in GitHub Actions across **Ubuntu, macOS, and Windows** on **Python 3.11, 3.12, and 3.13** (see [the workflow](.github/workflows/test.yml)). So the Windows test suite is genuinely green, but no one clicks through the running app on Windows before a release. Windows should work; it's just less traveled. If something is off there, that's a real bug and we want to hear about it.

## Getting help

Something broken, unclear, or just wrong? [**Open an issue**](https://github.com/AlteredCraft/chat-rag-explorer/issues) — include your OS, your Python version (`uv run python --version`), and what you expected versus what happened. Documentation gaps are legitimate issues; if you got stuck, the docs failed you.

Workshop attendees can also reach us at [info@alteredcraft.com](mailto:info@alteredcraft.com).

### Common snags

| Symptom | Fix |
|---------|-----|
| `uv: command not found` | Restart your terminal after installing uv so your `PATH` updates. |
| Port already in use | The app tries 8000–8004 automatically. To pin one, set `SERVER_PORT` in `.env`. |
| Models load, but sending a message fails | Expected if the key is bad — the catalog is public, so the picker fills regardless. Diagnose it as a key problem, not a model problem. |
| `401` / `User not found` | The key reached OpenRouter and was rejected. It's invalid, revoked, or belongs to a deleted account — reissue at [openrouter.ai/keys](https://openrouter.ai/keys). A correctly *formatted* key can still be rejected. |
| `402` / insufficient credits | The key is valid but the account is out of funds. [Add credit](https://openrouter.ai/settings/credits) or switch to a free model. |
| Key set but still unauthorized | `.env` is read at startup only. Stop the app with `Ctrl+C` and start it again. |
| Nothing in the model picker | Every ID in `.models_list` must exist upstream. Compare against [OpenRouter's catalog](https://openrouter.ai/models), or delete the file to show everything. |
| First RAG query hangs | It's downloading the ~79 MB embedding model. Let it finish once. |
| "No collections found" | Confirm the path is `data/chroma_db` and that the app has been started at least once — it creates that directory on first run. |

---

# Learn More

Deeper reference on architecture, testing, logging, and the release process.

## Features

*   **Inspect Request Details**: See the exact payload sent to the model — parameters, token counts, timing, and retrieved RAG documents with source metadata and similarity scores
*   **Real-time Streaming**: Server-Sent Events (SSE) stream responses token by token
*   **Model Selection**: Model picker populated from OpenRouter, filtered by `.models_list`
*   **Conversation History**: Multi-turn conversations with context retention
*   **Metrics Sidebar**: Live session metrics including token usage
*   **Markdown Support**: Secure rendering via Marked.js and DOMPurify (bundled locally, works offline)
*   **Clean UI**: Responsive interface in vanilla HTML/CSS/JS

## Model Selection

Two separate things decide which model a request uses: `.models_list` controls **which models are offered**, and `DEFAULT_MODEL` controls **which one is chosen when the user hasn't picked**.

### `.models_list` — what appears in the picker

OpenRouter exposes hundreds of models, many of them unsuited to chat. This file narrows the picker to a curated set that behaves well in RAG scenarios. Edit it to customize:

```
# One model ID per line, comments start with #
openai/gpt-5.6-luna
anthropic/claude-sonnet-4.5
google/gemini-3.6-flash
```

Blank lines and `#` comments are ignored. Browse [OpenRouter's catalog](https://openrouter.ai/models) for valid IDs — an ID that doesn't exist upstream simply won't appear.

Delete the file entirely to show every OpenRouter model (⚠️ hundreds of entries). The Settings page reports whether the filter is active and how many models it lists.

### `DEFAULT_MODEL` — what's selected before the user chooses

The default is declared once, in `config.py` (override it with the `DEFAULT_MODEL` environment variable). The frontend fetches it from `/api/status` on page load, so the chat page and the Settings picker always agree with the backend — there is nothing to keep in sync by hand.

Keep the default present in `.models_list` or it won't be selectable; `tests/unit/test_config.py` enforces that rule, so drift fails the suite rather than surfacing as a confusing runtime error.

> **Changed the default and nothing happened?** Your model choice is remembered in `localStorage` under `chat-rag-selected-model`, and a saved choice always wins over the default. To see the new default, pick a different model in Settings, or clear site data in your browser's DevTools (Application → Local Storage).

## Content Preparation

To ingest your own documents, see [utils/README.md](utils/README.md):

- **split.py** — split a large markdown file into chapters by heading pattern
- **ingest.py** — two-phase workflow: preview chunks → inspect → ingest to ChromaDB

The ingest tool writes human-readable chunk previews to `data/chunks/` so you can tune chunk size and overlap *before* committing anything to the vector database. Reading those previews is the fastest way to build intuition for what chunking actually does.

`data/corpus/` also ships with several other public-domain and open corpora (Benjamin Franklin's autobiography, Paul Graham essays, D&D SRD, WikiVoyage, and more) if you want something larger to experiment with.

## Architecture

### Project Structure

```text
chat-rag-explorer/
├── chat_rag_explorer/           # Main package
│   ├── static/                  # CSS, JS, and local libraries
│   ├── templates/               # HTML templates
│   ├── __init__.py              # App factory
│   ├── logging.py               # Centralized logging configuration
│   ├── routes.py                # Web endpoints
│   ├── services.py              # LLM integration logic
│   ├── rag_config_service.py    # ChromaDB connection management
│   ├── prompt_service.py        # System prompt CRUD operations
│   └── chat_history_service.py  # Conversation logging to JSONL
├── utils/                       # CLI utilities for content preparation
│   ├── README.md                # Utility documentation
│   ├── split.py                 # Split 1 page markdown into chapters
│   └── ingest.py                # Ingest markdown into ChromaDB
├── data/
│   ├── corpus/                  # Source markdown documents
│   ├── chunks/                  # Chunk previews for inspection (gitignored)
│   ├── chroma_db/               # Working ChromaDB databases (gitignored, auto-created)
│   └── chroma_db_sample/        # Pristine sample DB (copied to chroma_db/ on startup)
├── prompts/                     # System prompt templates (markdown)
├── logs/                        # Application logs (gitignored)
├── tests/                       # Test suite
├── config.py                    # Configuration settings (environment variable mapping)
├── main.py                      # Application entry point
├── pyproject.toml               # Dependencies and project metadata (uv)
├── .env.example                 # Template for environment variables (.env)
├── .env                         # Secrets and local overrides (gitignored)
└── .models_list                 # RAG-recommended models filter (see Model Selection)
```

### Design Patterns

*   **Modular Architecture**: Flask [Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/) and the [Application Factory](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) pattern
*   **Centralized Logging**: Request ID correlation and configurable log levels
*   **Modern Python Tooling**: `uv` for dependency management

## Configuration

All settings live in `.env` (copied from `.env.example`). Only `OPENROUTER_API_KEY` is required.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | **Required.** Your OpenRouter key |
| `CHROMADB_API_KEY` | — | Only for ChromaDB cloud mode |
| `SERVER_HOST` | `127.0.0.1` | Bind address |
| `SERVER_PORT` | `8000` | Starting port |
| `SERVER_PORT_RETRIES` | `5` | How many ports to try (8000–8004) |
| `LOG_LEVEL_APP` | `DEBUG` | Log level for application code |
| `LOG_LEVEL_DEPS` | `INFO` | Log level for dependencies (Flask, httpx, etc.) |
| `LOG_TO_STDOUT` | `true` | Output logs to console |
| `LOG_TO_FILE` | `true` | Write logs to file |
| `LOG_FILE_PATH` | `logs/app.log` | Path to log file |
| `CHAT_HISTORY_ENABLED` | `false` | Enable chat interaction logging |
| `CHAT_HISTORY_PATH` | `logs/chat-history.jsonl` | Path to chat history file |

## Logging

### Backend

**Startup Banner**: on start, logs a configuration summary with the API key masked:

```
============================================================
RAG Lab - Starting up
============================================================
Configuration:
  - OpenRouter Base URL: https://openrouter.ai/api/v1
  - OpenRouter API Key: sk-or-v1...6a0d
  - Default Model: deepseek/deepseek-v4-flash
============================================================
```

**Request Correlation**: every API request carries a unique 8-character request ID, so you can follow one request through the whole log:

```
[a1b2c3d4] POST /api/chat - Model: openai/gpt-4, Messages: 3, Content length: 150 chars
[a1b2c3d4] Starting chat stream - Model: openai/gpt-4
[a1b2c3d4] Token usage - Prompt: 45, Completion: 120, Total: 165
[a1b2c3d4] POST /api/chat - Stream completed (1.523s, 42 chunks)
```

**Performance Metrics**: timing for requests, including time-to-first-chunk (TTFC) for streams.

### Frontend

The browser console carries structured logs with session tracking:

```
[2025-12-26T15:30:00.000Z] [sess_abc123] INFO: Chat request initiated {model: "openai/gpt-4", messageLength: 50}
[2025-12-26T15:30:01.500Z] [sess_abc123] DEBUG: Time to first chunk {ttfc_ms: "823.45"}
[2025-12-26T15:30:02.000Z] [sess_abc123] INFO: Chat response completed {chunks: 42, totalTime_ms: "1523.00"}
```

Open DevTools ([F12](https://developer.chrome.com/docs/devtools/open)) → Console to view them.

## Testing

pytest with randomized test ordering, to catch tests that secretly depend on each other.

```bash
uv run pytest                     # Run all tests (randomized order)
uv run pytest -v                  # Verbose output
uv run pytest -x                  # Stop on first failure
uv run pytest --cov               # Run with coverage report
uv run pytest -k "test_name"      # Run a specific test by name
```

### Multi-Version Testing

[nox](https://nox.thea.codes/) runs the suite across Python 3.11, 3.12, and 3.13 — the same versions CI uses:

```bash
uv run nox                        # Run on all Python versions
uv run nox -s tests-3.12          # Run on a specific version
uv run nox -- -x                  # Pass args through to pytest
```

### Test Philosophy

*   **Unit tests** live in `tests/unit/` and must not make network calls
*   External dependencies (ChromaDB, OpenRouter) are mocked
*   Use the `tmp_path` fixture for file operations
*   Tests run in random order to surface hidden state dependencies

## Release Process

This project uses [Release Please](https://github.com/googleapis/release-please) for automated versioning and changelog generation.

**How it works:**
1. All commits to `main` use [Conventional Commits](https://www.conventionalcommits.org/) format
2. Release Please opens or updates a Release PR with the version bump and changelog
3. Merge the Release PR to cut a release
4. A GitHub Release and git tag are created automatically

**Commit format:**

| Prefix | Description | Version Bump |
|--------|-------------|--------------|
| `feat:` | New feature | Minor (0.1.0 → 0.2.0) |
| `fix:` | Bug fix | Patch (0.1.0 → 0.1.1) |
| `feat!:` or `fix!:` | Breaking change | Major (0.1.0 → 1.0.0) |
| `docs:` | Documentation | Patch |
| `chore:` | Maintenance | No Release PR triggered; rolls into the next release |

```bash
git commit -m "feat: add dark mode toggle"
git commit -m "fix: correct token count in sidebar"
git commit -m "feat!: redesign REST API endpoints"
```

## License

Open source under the [MIT License](LICENSE).
