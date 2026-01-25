# Workshop Prework

Welcome! Complete these steps before the [workshop](https://alteredcraft.github.io/workshop-rag-basics/) to set up your environment.

**We appreciate your best effort**—show up even if you don't finish everything. Helpers will be available at the workshop to assist with setup issues. We also ask those attending with more tech experience to help others get set up.

Need help before the workshop? Email info@alteredcraft.com

---

## 0. Terminal Basics

We'll use the terminal in portions of the course. New to command lines? Check these guides:
- [Windows Terminal](https://docs.microsoft.com/en-us/windows/terminal/get-started)
- [Mac Terminal](https://support.apple.com/guide/terminal/welcome/mac)
- [Linux Terminal](https://documentation.ubuntu.com/desktop/en/latest/tutorial/the-linux-command-line-for-beginners/)

---

## 1. Install uv

uv manages Python versions and dependencies. Install it for your OS: [uv installation](https://docs.astral.sh/uv/getting-started/installation/)

---

## 2. Get the Code

Clone the repo (requires [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)):

```bash
git clone https://github.com/AlteredCraft/chat-rag-explorer.git
cd chat-rag-explorer
```

Note: If Git or clone is just not cooperating, [download the ZIP](https://github.com/AlteredCraft/chat-rag-explorer/archive/refs/heads/main.zip) from the repo page and extract it, then `cd` into the extracted folder.

---

## 3. Install Dependencies

```bash
uv sync
```

This installs Python 3.13 and all packages in an isolated environment.

---

## You made it!! 

Feel free to take a peek at the running chat app before the workshop. We will cover everything in detail during the session, including prepareing a RAG data source for use in the web app.

```bash
uv run main.py
```

Open the URL shown (ex: `🚀 Running on: 127.0.0.1:8000`). 
You'll see a message about a missing API key—that's expected! You'll receive one at the workshop.

---

## Troubleshooting

- **"uv: command not found"** — Restart your terminal after installing uv
- **Port in use** — The app tries ports 8001-8004 automatically. If all fail, close other apps using those ports

Still stuck? Email info@alteredcraft.com
