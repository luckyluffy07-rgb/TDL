# TDL — AI Chatbot 🤖

A beginner-friendly **command-line chatbot** that talks to OpenAI's GPT models, written in Python. Type messages in your terminal, and an AI replies — it remembers the whole conversation, so you can chat back and forth.

```
$ python chatbot.py
============================================================
  TDL Chatbot — powered by OpenAI
  Model: gpt-5-mini
  Type /help for commands, or just start chatting!
============================================================

You: hi! what can you do?
TDL Bot: Hi! I can answer questions, explain ideas, help write things...
```

## What you need

- **Python 3.10 or newer** — check with `python --version`
- An **OpenAI API key** — see step 3 below
- Internet connection

> **Note:** an OpenAI *API key* is separate from a ChatGPT subscription. API usage is pay-per-request, but the default model (`gpt-5-mini`) is very cheap — a casual chat typically costs less than a cent. See [OpenAI pricing](https://platform.openai.com/docs/pricing).

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

### 3. Get an OpenAI API key

1. Go to **https://platform.openai.com/api-keys**
2. Log in (or sign up), click **"Create new secret key"**, and copy it
3. If asked, add a small amount of credit for API usage in Billing

### 4. Create your `.env` file

```bash
cp .env.example .env
```

Then open `.env` in any editor and paste your key:

```
OPENAI_API_KEY=sk-your-real-key-here
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
| `/model`  | Show which model you're talking to    |
| `exit` / `quit` / `bye` | Leave the chat       |

## Customizing

All settings live in your `.env` file:

```bash
# Use a different model — e.g. the flagship
OPENAI_MODEL=gpt-5.5

# Give the bot a personality
CHATBOT_SYSTEM_PROMPT=You are a pirate. Always say "arr".
```

## How it works (code tour)

The whole bot is one file, [`chatbot.py`](chatbot.py), about 150 lines:

1. **`load_config()`** — reads your API key and settings from `.env`
2. **`get_reply()`** — sends the conversation to OpenAI using the **Responses API**
3. **`main()`** — the chat loop: reads your input, calls the AI, prints the reply

The trick that makes it "remember" the conversation: the full history of
messages is re-sent with every request, so each reply has the whole context.

## Running the tests

The tests run offline (no API key needed):

```bash
python -m unittest test_chatbot.py -v
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `No OPENAI_API_KEY found` | You skipped step 4 — create the `.env` file |
| `Invalid API key` | Re-copy the key from platform.openai.com (no extra spaces) |
| `Rate limit or quota reached` | You hit a usage limit — wait a minute, or check billing |
| `Could not reach OpenAI` | Check your internet connection |
| `ModuleNotFoundError: No module named 'openai'` | Activate your virtualenv, then `pip install -r requirements.txt` |

## Project structure

```
TDL/
├── chatbot.py       # the whole chatbot
├── test_chatbot.py  # offline unit tests
├── requirements.txt # Python dependencies
├── .env.example     # template for your API key settings
├── .env             # your secret key (never committed) — you create this
└── .gitignore       # tells git to ignore .env, .venv, etc.
```

## Ideas to extend it

- 🌈 Stream replies token-by-token (`stream=True`)
- 💾 Save conversation history to a file
- 🎨 Build a web interface with Flask or Streamlit
- 🧠 Add a `/translate` or `/summarize` command using a different system prompt
