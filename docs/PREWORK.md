# Workshop Prework

Welcome! Complete these steps before the [workshop](https://alteredcraft.github.io/workshop-rag-basics/) so we can spend the session on RAG rather than on installs.

Budget about 15 minutes. **We appreciate your best effort** — show up even if you don't finish. Helpers will be available to sort out setup issues, and we ask attendees with more experience to lend a hand to those with less.

Stuck beforehand? Email [info@alteredcraft.com](mailto:info@alteredcraft.com) or [open an issue](https://github.com/AlteredCraft/chat-rag-explorer/issues).

---

## 0. Terminal Basics

We use the terminal throughout the course. New to command lines? Skim one of these first:

- [macOS Terminal](https://support.apple.com/guide/terminal/welcome/mac)
- [Windows Terminal](https://learn.microsoft.com/en-us/windows/terminal/)
- [Linux Terminal](https://documentation.ubuntu.com/desktop/en/latest/tutorial/the-linux-command-line-for-beginners/)

You only need the basics: how to open it, how to change directory (`cd`), and how to run a command.

---

## 1. Install uv

[uv](https://docs.astral.sh/uv/getting-started/installation/) manages Python versions and packages for this project. Follow the instructions there for your OS.

You do **not** need to install Python yourself — uv handles that in step 3.

After installing, open a **new** terminal window and check it worked:

```bash
uv --version
```

---

## 2. Get the Code

Clone the repo (requires [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)):

```bash
git clone https://github.com/AlteredCraft/chat-rag-explorer.git
cd chat-rag-explorer
```

No Git, or the clone won't cooperate? [Download the ZIP](https://github.com/AlteredCraft/chat-rag-explorer/archive/refs/heads/main.zip), extract it, and `cd` into the extracted folder.

---

## 3. Install Dependencies

From inside the `chat-rag-explorer` directory:

```bash
uv sync
```

This installs Python 3.13 and every package the project needs into an isolated `.venv/` folder. Nothing lands on your system Python, and deleting the project folder removes it all.

---

## 4. Check It Works

```bash
uv run pytest
```

All tests should pass. They run fully offline — no API key required — so this confirms your environment is sound.

---

## You made it!

Feel free to take a peek at the app before the workshop. We'll cover everything in detail during the session, including preparing a RAG data source.

```bash
uv run main.py
```

Open the URL shown (e.g. `🚀 Running on: 127.0.0.1:8000`). Press `Ctrl+C` in the terminal to stop it.

The terminal will warn about a missing `.env` file and API key, and the app will say the same in the browser — **that's expected.** You'll receive a key at the workshop. The app still starts, so you can click around beforehand.

### When you get your key

Two steps, and you can do them during the session:

```bash
cp .env.example .env
```

Then open `.env` and paste the key into `LLM_API_KEY`. That's the only line you need to change — the file already selects OpenRouter as the provider.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uv: command not found` | Open a new terminal after installing uv so your `PATH` refreshes. |
| `git: command not found` | [Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), or use the ZIP download in step 2. |
| Port in use | The app tries 8000–8004 automatically. If all are taken, close whatever is using them. |
| `uv sync` fails behind a corporate proxy/VPN | Try off the VPN, or bring it to the workshop and we'll sort it out. |

A note on platforms: development and hands-on testing happen on **macOS**, while automated tests also cover **Windows and Linux**. All three should work for the workshop. If Windows gives you trouble, tell us — [open an issue](https://github.com/AlteredCraft/chat-rag-explorer/issues) or flag it at the session.

Still stuck? Email [info@alteredcraft.com](mailto:info@alteredcraft.com) — and please come anyway, we'll get you running.
