# Chat RAG Explorer

An educational application designed to demonstrate the implementation of a Chat interface with Large Language Models (LLMs) and, in future steps, Retrieval-Augmented Generation (RAG).

This project uses **Flask** for the backend, **OpenRouter** for LLM access (supporting models like GPT-4, Claude 3, Llama 3, etc.), and **vanilla JavaScript** for a clean, streaming chat interface.

## 🚀 Features

*   **Real-time Streaming**: Implements Server-Sent Events (SSE) logic to stream LLM responses token-by-token.
*   **Model Selection**: Settings page with a dynamic model picker that fetches all available models from OpenRouter, grouped by provider with pricing and context length details.
*   **Conversation History**: Full multi-turn conversation support, allowing the LLM to remember context throughout the session.
*   **Metrics Sidebar**: A dedicated right-hand sidebar displaying real-time session metrics, including model identification and token usage (prompt, completion, total).
*   **Markdown Support**: Securely renders Markdown (including lists, code blocks, and formatting) using Marked.js and DOMPurify for sanitization. Works offline.
*   **Modular Architecture**: Organized following Flask best practices (Blueprints, Application Factory pattern).
*   **Centralized Logging**: Request ID correlation, performance metrics, and configurable log levels for app and dependencies. See [Logging](#-logging) section for details.
*   **OpenRouter Integration**: Easy access to various state-of-the-art models via a single API.
*   **Clean UI**: A responsive, modern chat interface built with raw HTML/CSS/JS (no heavy frontend frameworks).
*   **Modern Python Tooling**: Uses `uv` for blazing fast dependency management.

## 🛠 Prerequisites

*   Python 3.13+
*   [uv](https://github.com/astral-sh/uv) (for package management)
*   An [OpenRouter](https://openrouter.ai/) API Key

## ⚡️ Quick Start

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/chat-rag-explorer.git
    cd chat-rag-explorer
    ```

2.  **Set up the environment variables**
    Create a `.env` file in the root directory:
    ```bash
    cp .env.example .env
    ```
    Add your API key and optional configuration to `.env`:
    ```env
    OPENROUTER_API_KEY=sk-or-v1-your-key-here
    
    # Logging Configuration
    LOG_LEVEL_APP=DEBUG
    LOG_LEVEL_DEPS=INFO
    LOG_TO_STDOUT=true
    LOG_TO_FILE=true
    LOG_FILE_PATH=app.log
    ```

3.  **Run the application**
    Use `uv` to sync dependencies and run the server:
    ```bash
    uv run main.py
    ```

    > **Port in use?** If port 5005 is taken, edit the `port` variable in `main.py`.

4.  **Explore**
    Open your browser to [http://127.0.0.1:5005](http://127.0.0.1:5005).

## 📂 Project Structure

```text
chat-rag-explorer/
├── chat_rag_explorer/       # Main package
│   ├── static/              # CSS, JS, and local libraries
│   │   ├── script.js        # Main chat interface logic
│   │   ├── settings.js      # Settings page logic (model picker)
│   │   ├── style.css        # Application styles
│   │   ├── marked.min.js    # Markdown parser (offline)
│   │   └── purify.min.js    # HTML sanitizer (offline)
│   ├── templates/           # HTML templates
│   │   ├── index.html       # Main chat interface
│   │   └── settings.html    # Settings page (model selection)
│   ├── __init__.py          # App factory
│   ├── logging.py           # Centralized logging configuration
│   ├── routes.py            # Web endpoints
│   └── services.py          # LLM integration logic
├── docs/
│   └── adr/                 # Architecture Decision Records (ADRs)
├── config.py                # Configuration settings (environment variable mapping)
├── main.py                  # Application entry point
├── pyproject.toml           # Dependencies and project metadata (uv)
└── .env                     # Secrets and local overrides (gitignored)
```

## 🏗 Architectural Decisions

This project maintains Architecture Decision Records (ADRs) to document significant design choices and their rationale. You can find them in the `docs/adr/` directory. These are excellent resources for understanding *why* certain technologies or patterns were chosen.

## 📋 Logging

The application features a comprehensive logging system for debugging and monitoring.

### Configuration

Set these environment variables in your `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL_APP` | `DEBUG` | Log level for application code |
| `LOG_LEVEL_DEPS` | `INFO` | Log level for dependencies (Flask, httpx, etc.) |
| `LOG_TO_STDOUT` | `true` | Output logs to console |
| `LOG_TO_FILE` | `true` | Write logs to file |
| `LOG_FILE_PATH` | `app.log` | Path to log file |

### Backend Logging

**Startup Banner**: On application start, logs configuration summary with masked API key:
```
============================================================
Chat RAG Explorer - Starting up
============================================================
Configuration:
  - OpenRouter Base URL: https://openrouter.ai/api/v1
  - OpenRouter API Key: sk-or-v1...6a0d
  - Default Model: openai/gpt-3.5-turbo
============================================================
```

**Request Correlation**: All API requests include a unique request ID for tracing:
```
[a1b2c3d4] POST /api/chat - Model: openai/gpt-4, Messages: 3, Content length: 150 chars
[a1b2c3d4] Starting chat stream - Model: openai/gpt-4
[a1b2c3d4] Token usage - Prompt: 45, Completion: 120, Total: 165
[a1b2c3d4] POST /api/chat - Stream completed (1.523s, 42 chunks)
```

**Performance Metrics**: Timing information for requests, including time-to-first-chunk (TTFC) for streams.

### Frontend Logging

The browser console includes structured logs with session tracking:
```
[2025-12-26T15:30:00.000Z] [sess_abc123] INFO: Chat request initiated {model: "openai/gpt-4", messageLength: 50}
[2025-12-26T15:30:01.500Z] [sess_abc123] DEBUG: Time to first chunk {ttfc_ms: "823.45"}
[2025-12-26T15:30:02.000Z] [sess_abc123] INFO: Chat response completed {chunks: 42, totalTime_ms: "1523.00"}
```

Open browser DevTools (F12) → Console to view frontend logs.

## 📚 Roadmap

*   [x] Basic Chat Interface
*   [x] LLM Streaming
*   [x] Conversation History (Multi-turn)
*   [x] Metrics Sidebar (Token usage & Model info)
*   [x] Settings Page with Model Selection
*   [ ] **RAG Implementation**: Connect a vector database to query local documents.
*   [ ] Further settings and metrics for Chat UI
*   [ ] Chat History Persistence (Server-side)

## 📝 License

This project is open source and available under the [MIT License](LICENSE).
