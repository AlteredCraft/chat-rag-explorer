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
*   **Centralized Logging**: Configurable logging for the app (DEBUG) and dependencies (INFO). Includes raw LLM response logging in `DEBUG` mode for inspecting provider metadata.
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
    cp .env.example .env  # If example exists, otherwise create manually
    ```
    Add your API key and optional configuration to `.env`:
    ```env
    OPENROUTER_API_KEY=sk-or-v1-your-key-here
    
    # Optional Logging Configuration
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

## 📚 Roadmap

*   [x] Basic Chat Interface
*   [x] LLM Streaming
*   [x] Conversation History (Multi-turn)
*   [x] Metrics Sidebar (Token usage & Model info)
*   [x] Settings Page with Model Selection
*   [ ] **RAG Implementation**: Connect a vector database to query local documents.
*   [ ] File Upload Support
*   [ ] Chat History Persistence (Server-side)

## 📝 License

This project is open source and available under the [MIT License](LICENSE).
