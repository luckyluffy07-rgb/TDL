# TDL — AI Chatbot 🤖

A beginner-friendly **command-line chatbot** in Python. It talks to **Google Gemini** — which has a **free tier** — and can also use **OpenAI** if you prefer. It remembers the whole conversation, so you can chat back and forth.

```
$ python chatbot.py
============================================================
  TDL Chatbot
  AI: Google Gemini — gemini-3.8-flash
  Type /help for commands, or just start chatting!
============================================================

You: hi! what can you do?
TDL Bot: Hi! I can answer questions, explain ideas, help write things...
```

## What you need

- **Python 3.10 or newer** — check with `python --version`
- A **Gemini API key** (free, no credit card) — see step 3 below
- Internet connection

> 💡 **Why Gemini by default?** Google's Gemini API has a free tier with rate limits generous enough for a personal chatbot, and getting a key needs nothing but a Google account. OpenAI works too (set `PROVIDER=openai`), but its API is pay-per-use — a ChatGPT subscription does **not** cover it.

## Setup (one time)

### 1. Clone the repo and open it

```bash
git clone https://github.com/luckyluffy07-rgb/TDL.git
cd TDL
```

### 2. Create a virtual environment and install dependencies

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Get a FREE Gemini API key

1. Go to **https://aistudio.google.com/apikey**
2. Sign in with your Google account
3. Click **"Get API key"** (or "Create API key") and copy it — it starts with `AIza`

No credit card, no billing setup. The free tier is rate-limited (plenty for personal use); if you ever hit a limit, the bot tells you to wait a minute.

### 4. Create your `.env` file

```bash
cp .env.example .env
```

Then open `.env` in any editor and paste your key:

```
GEMINI_API_KEY=AIza-your-real-key-here
```

> ⚠️ **Never commit your API key to GitHub.** The `.env` file is already listed in `.gitignore`, so git will not upload it. Only `.env.example` (a template with no real key) is committed.

### 5. Run it!

```bash
python chatbot.py
```

## Chat commands

| Command   | What it does                          |
|-----------|---------------------------------------|
| `/help`   | Show the command list                 |
| `/new`    | Start a fresh conversation (clears history) |
| `/model`  | Show which AI provider and model you're talking to |
| `exit` / `quit` / `bye` | Leave the chat       |

## Customizing

All settings live in your `.env` file:

```bash
# Use a different Gemini model (e.g. a lighter, faster one)
GEMINI_MODEL=gemini-3.5-flash

# Give the bot a personality
CHATBOT_SYSTEM_PROMPT=You are a pirate. Always say "arr".
```

### Using OpenAI instead (optional, paid)

```bash
PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). API usage is pay-per-request and separate from any ChatGPT subscription — the default model `gpt-5-mini` costs fractions of a cent per chat message. If both keys are set and `PROVIDER` is unset, Gemini (the free one) wins.

## How it works (code tour)

The whole bot is one file, [`chatbot.py`](chatbot.py), about 250 lines:

1. **`load_config()`** — reads your keys and settings from `.env`, auto-detects the provider (Gemini if `GEMINI_API_KEY` is set, else OpenAI)
2. **`GeminiBackend` / `OpenAIBackend`** — small classes that both expose the same `.reply(history)` method, so the chat loop doesn't care which AI it's talking to
3. **`main()`** — the chat loop: reads your input, calls the backend, prints the reply

The trick that makes it "remember" the conversation: the full history of messages is re-sent with every request, so each reply has the whole context.

## Running the tests

The tests run offline (no API key or network needed):

```bash
python -m unittest test_chatbot.py -v
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `No API key found` | You skipped step 4 — create the `.env` file |
| `Gemini rejected your API key` | Re-copy the key from aistudio.google.com/apikey (no extra spaces) |
| `Gemini rate limit hit` | Free tier limit — wait a minute and try again |
| `Could not reach Google` | Check your internet connection |
| `ModuleNotFoundError: No module named 'google'` | Activate your virtualenv, then `pip install -r requirements.txt` |
| `Invalid OpenAI API key` | You're using `PROVIDER=openai` — check `OPENAI_API_KEY` |

## Project structure

```
TDL/
├── chatbot.py       # the whole chatbot (Gemini + OpenAI backends)
├── web_app.py       # web version: Flask server reusing those backends
├── static/
│   └── index.html   # the chat web UI (HTML + CSS + JS, no build step)
├── test_chatbot.py  # offline unit tests
├── requirements.txt # Python dependencies
├── .env.example     # template for your API key settings
├── .env             # your secret key (never committed) — you create this
└── .gitignore       # tells git to ignore .env, .venv, etc.
```

## Ideas to extend it

- 🌈 Stream replies token-by-token
- 💾 Save conversation history to a file
- 🧠 Add a `/translate` or `/summarize` command using a different system prompt

## 🌐 Web version

Prefer a browser to the terminal? `web_app.py` serves the same chatbot as a
web page, reusing the exact same `.env` settings and provider backends.

```bash
pip install -r requirements.txt
cp .env.example .env      # then paste your API key in
python web_app.py
```

Open **http://localhost:5000** and start chatting.

Features:

- Chat bubbles with a typing indicator
- **New chat** button to clear the conversation
- Enter to send, Shift+Enter for a new line
- Friendly error messages (bad key, rate limit, no connection)

Set a different port with `PORT=8080 python web_app.py`.

### How it works

| Route | What it does |
| --- | --- |
| `GET /` | serves the chat page from `static/index.html` |
| `GET /api/info` | reports the active provider and model |
| `POST /api/chat` | takes `{"messages": [...]}` and returns `{"reply": "..."}` |

Conversation history is kept in the browser and sent with each request, so the
server stays stateless. Only the last 40 messages are forwarded to the AI to
keep requests small.

> **Note:** this uses Flask's development server, which is fine for local use.
> To expose it publicly, run it behind a production WSGI server such as
> `gunicorn -b 0.0.0.0:5000 web_app:app` and don't share your API key.
