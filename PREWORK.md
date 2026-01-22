# Workshop Prework

Complete these steps **before** the workshop.

---

## 1. Install uv

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installation.

---

## 2. Get the Code

```bash
git clone https://github.com/YOUR_ORG/chat-rag-explorer.git
cd chat-rag-explorer
```

Or download ZIP from the GitHub repo page.

---

## 3. Install Dependencies

```bash
uv sync
```

This automatically installs Python 3.13 and all packages in a virtual environment just for this project.

---

## 4. Run Tests

```bash
uv run pytest
```

All tests should pass.

---

## 5. Start the App

```bash
uv run main.py
```

In the output you will see the URL to open in your browser, `🚀 Running on: 127.0.0.1:8000` (usually http://localhost:8000). Open it.


You'll see a message about the missing API key - that's expected! You'll receive an API key at the workshop.
---

## Troubleshooting

**"uv: command not found"** - Restart your terminal after installing uv.

**Tests fail** - Run `uv sync` again, then retry.

**Port in use** - The app auto-tries ports 8001-8004 if 8000 is busy.
