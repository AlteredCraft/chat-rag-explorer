# Chat RAG Explorer

An educational application designed to demonstrate the implementation of a Chat interface with Large Language Models (LLMs) and, in future steps, Retrieval-Augmented Generation (RAG).

This project uses **Flask** for the backend, **OpenRouter** for LLM access (supporting models like GPT-4, Claude 3, Llama 3, etc.), and **vanilla JavaScript** for a clean, streaming chat interface.

## 🚀 Features

*   **Real-time Streaming**: Implements Server-Sent Events (SSE) logic to stream LLM responses token-by-token.
*   **Markdown Support**: Securely renders Markdown (including lists, code blocks, and formatting) using Marked.js and DOMPurify for sanitization. Works offline.
*   **Modular Architecture**: Organized following Flask best practices (Blueprints, Application Factory pattern).
*   **Centralized Logging**: Configurable logging for the app (DEBUG) and dependencies (INFO) with support for stdout and file output.
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
    Add your API key to `.env`:
    ```env
    OPENROUTER_API_KEY=sk-or-v1-your-key-here
    ```

3.  **Run the application**
    Use `uv` to sync dependencies and run the server:
    ```bash
    uv run main.py
    ```

4.  **Explore**
    Open your browser to [http://127.0.0.1:5000](http://127.0.0.1:5000).

## 📂 Project Structure

```text
chat-rag-explorer/
├── chat_rag_explorer/   # Main package
│   ├── static/          # CSS and JavaScript
│   ├── templates/       # HTML templates
│   ├── __init__.py      # App factory
│   ├── routes.py        # Web endpoints
│   └── services.py      # LLM integration logic
├── config.py            # Configuration settings
├── main.py              # Application entry point
├── pyproject.toml       # Dependencies (uv)
└── .env                 # Secrets (gitignored)
```

## 📚 Roadmap

*   [x] Basic Chat Interface
*   [x] LLM Streaming
*   [ ] **RAG Implementation**: Connect a vector database to query local documents.
*   [ ] File Upload Support
*   [ ] Chat History Persistence

## 📝 License

This project is open source and available under the [MIT License](LICENSE).
