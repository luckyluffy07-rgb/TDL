#!/usr/bin/env python3
"""
TDL Chatbot — a command-line AI assistant powered by OpenAI.

Usage:
    python chatbot.py

Before running, copy .env.example to .env and paste your OpenAI API key.
Your key lives in .env (which git ignores), so it never gets committed.
"""

import os
import sys

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

# --- Configuration -----------------------------------------------------------

DEFAULT_MODEL = "gpt-5-mini"  # cheap and capable; change via OPENAI_MODEL in .env

DEFAULT_SYSTEM_PROMPT = (
    "You are TDL Bot, a friendly and helpful AI assistant running in a "
    "terminal. Keep your answers clear and concise, and format them for "
    "plain-text reading (no heavy markdown)."
)

EXIT_WORDS = {"exit", "quit", "bye", "/exit", "/quit"}

HELP_TEXT = """Commands:
  /help      show this help
  /new       start a fresh conversation (clears history)
  /model     show which model you are talking to
  exit/quit  leave the chat

Anything else you type is sent to the AI."""


# --- Setup --------------------------------------------------------------------

def load_config() -> dict:
    """Read settings from the environment (loaded from the .env file)."""
    load_dotenv()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: No OPENAI_API_KEY found.")
        print()
        print("To fix this:")
        print("  1. Create an API key at https://platform.openai.com/api-keys")
        print("  2. Copy the .env.example file to a file named .env")
        print("  3. Open .env and set OPENAI_API_KEY=<your key>")
        print()
        print("(.env is in .gitignore, so your key stays out of GitHub.)")
        sys.exit(1)

    return {
        "api_key": api_key,
        "model": os.environ.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL,
        "system_prompt": (
            os.environ.get("CHATBOT_SYSTEM_PROMPT", "").strip()
            or DEFAULT_SYSTEM_PROMPT
        ),
    }


# --- Talking to the AI --------------------------------------------------------

def get_reply(client: OpenAI, *, model: str, system_prompt: str,
              history: list[dict]) -> str:
    """Send the whole conversation to OpenAI and return the assistant's reply.

    The Responses API is stateless per call, so we re-send the full history
    each turn — that's how the bot "remembers" the conversation.
    """
    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=history,
    )
    return response.output_text


# --- Main loop ----------------------------------------------------------------

def main() -> None:
    config = load_config()
    client = OpenAI(api_key=config["api_key"])
    model = config["model"]
    system_prompt = config["system_prompt"]

    print("=" * 60)
    print("  TDL Chatbot — powered by OpenAI")
    print(f"  Model: {model}")
    print("  Type /help for commands, or just start chatting!")
    print("=" * 60)

    history: list[dict] = []  # [{"role": "user"|"assistant", "content": "..."}]

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in EXIT_WORDS:
            print("Goodbye! 👋")
            break
        if lowered == "/help":
            print(HELP_TEXT)
            continue
        if lowered == "/new":
            history.clear()
            print("(Started a new conversation.)")
            continue
        if lowered == "/model":
            print(f"Currently using: {model}")
            continue

        history.append({"role": "user", "content": user_input})

        try:
            print("\nTDL Bot: ", end="", flush=True)
            reply = get_reply(client, model=model, system_prompt=system_prompt,
                              history=history)
            print(reply)
        except AuthenticationError:
            print("❌ Invalid API key — check OPENAI_API_KEY in your .env file.")
            history.pop()  # drop the failed turn so history stays clean
        except RateLimitError:
            print("⏳ Rate limit or quota reached — wait a moment and try again.")
            history.pop()
        except APIConnectionError:
            print("🌐 Could not reach OpenAI — check your internet connection.")
            history.pop()
        except APIStatusError as exc:
            print(f"⚠️ OpenAI returned an error (HTTP {exc.status_code}): {exc.message}")
            history.pop()
        else:
            history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
