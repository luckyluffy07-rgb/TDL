#!/usr/bin/env python3
"""
TDL Chatbot — a command-line AI assistant powered by Google Gemini or OpenAI.

Usage:
    python chatbot.py

Before running, copy .env.example to .env and add an API key:
  * Google Gemini (default, FREE): https://aistudio.google.com/apikey
  * OpenAI (optional, pay-per-use): https://platform.openai.com/api-keys

Your key lives in .env (which git ignores), so it never gets committed.
"""

import os
import sys

from dotenv import load_dotenv

# --- Configuration -----------------------------------------------------------

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"  # free tier — see ai.google.dev/gemini-api/docs/models
DEFAULT_OPENAI_MODEL = "gpt-5-mini"        # cheap OpenAI model (paid, pay-per-use)

PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "openai": "OpenAI",
}

DEFAULT_SYSTEM_PROMPT = (
    "You are TDL Bot, a friendly and helpful AI assistant running in a "
    "terminal. Keep your answers clear and concise, and format them for "
    "plain-text reading (no heavy markdown)."
)

EXIT_WORDS = {"exit", "quit", "bye", "/exit", "/quit"}

HELP_TEXT = """Commands:
  /help      show this help
  /new       start a fresh conversation (clears history)
  /model     show which AI provider and model you're talking to
  exit/quit  leave the chat

Anything else you type is sent to the AI."""


class ChatbotError(Exception):
    """A friendly error message that can be shown straight to the user."""


def _fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


# --- SDK imports (lazy: only the provider you use needs to be installed) -----

def _import_gemini():
    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as exc:
        raise ChatbotError(
            "The google-genai package is missing. Run:  pip install google-genai"
        ) from exc
    return genai, types, errors


def _import_openai():
    try:
        from openai import (
            APIConnectionError,
            APIStatusError,
            AuthenticationError,
            OpenAI,
            RateLimitError,
        )
    except ImportError as exc:
        raise ChatbotError(
            "The openai package is missing. Run:  pip install openai"
        ) from exc
    return OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError


# --- Backends: one class per AI provider -------------------------------------
#
# Both backends expose the same interface:
#     .reply(history) -> str
# where history is a list like
#     [{"role": "user"|"assistant", "content": "..."}, ...]
# and both raise ChatbotError with a human-friendly message on failure.


class GeminiBackend:
    """Talks to Google Gemini — has a free tier (https://aistudio.google.com/apikey)."""

    def __init__(self, api_key: str, model: str, system_prompt: str):
        genai, types, self._errors = _import_gemini()
        self.client = genai.Client(api_key=api_key)
        self.types = types
        self.model = model
        self.system_prompt = system_prompt

    def reply(self, history: list[dict]) -> str:
        # Gemini expects roles "user"/"model" (not "assistant") and the text
        # wrapped in "parts".
        contents = [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in history
        ]
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=self.types.GenerateContentConfig(
                    system_instruction=self.system_prompt
                ),
            )
        except self._errors.ClientError as exc:
            if exc.code == 429:
                raise ChatbotError(
                    "⏳ Gemini rate limit hit (free tier). Wait a minute and try again."
                ) from exc
            if exc.code in (401, 403):
                raise ChatbotError(
                    "❌ Gemini rejected your API key — check GEMINI_API_KEY in .env."
                ) from exc
            if exc.code in (400, 404):
                raise ChatbotError(
                    f"⚠️ Gemini rejected the request (HTTP {exc.code}: {exc.message}). "
                    "If the model name is wrong, set GEMINI_MODEL in .env."
                ) from exc
            raise ChatbotError(
                f"⚠️ Gemini error (HTTP {exc.code}): {exc.message}"
            ) from exc
        except self._errors.ServerError as exc:
            raise ChatbotError(
                "🛠️ Gemini is having server issues — try again in a moment."
            ) from exc
        except Exception as exc:  # network problems, timeouts, ...
            raise ChatbotError(
                "🌐 Could not reach Google — check your internet connection."
            ) from exc

        if not response.text:
            raise ChatbotError(
                "⚠️ Gemini returned no text (the reply may have been blocked). "
                "Try rephrasing your message."
            )
        return response.text


class OpenAIBackend:
    """Talks to OpenAI — pay-per-use (https://platform.openai.com/api-keys)."""

    def __init__(self, api_key: str, model: str, system_prompt: str):
        (
            openai_client,
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            APIStatusError,
        ) = _import_openai()
        self.client = openai_client(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self._auth_error = AuthenticationError
        self._rate_limit_error = RateLimitError
        self._connection_error = APIConnectionError
        self._status_error = APIStatusError

    def reply(self, history: list[dict]) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=self.system_prompt,
                input=history,
            )
        except self._auth_error:
            raise ChatbotError(
                "❌ Invalid OpenAI API key — check OPENAI_API_KEY in your .env file."
            ) from None
        except self._rate_limit_error:
            raise ChatbotError(
                "⏳ OpenAI rate limit or quota reached — wait a moment and try again."
            ) from None
        except self._connection_error:
            raise ChatbotError(
                "🌐 Could not reach OpenAI — check your internet connection."
            ) from None
        except self._status_error as exc:
            raise ChatbotError(
                f"⚠️ OpenAI returned an error (HTTP {exc.status_code}): {exc.message}"
            ) from exc
        except Exception as exc:  # anything unexpected
            raise ChatbotError(f"⚠️ Unexpected error: {exc}") from exc
        return response.output_text


# --- Setup --------------------------------------------------------------------

def load_config() -> dict:
    """Read settings from the environment (loaded from the .env file)."""
    load_dotenv()

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    provider = os.environ.get("PROVIDER", "").strip().lower() or None

    if provider and provider not in PROVIDER_LABELS:
        _fail(f"PROVIDER must be 'gemini' or 'openai', not {provider!r}.")
    if provider == "gemini" and not gemini_key:
        _fail("PROVIDER is set to 'gemini' but GEMINI_API_KEY is missing from .env.")
    if provider == "openai" and not openai_key:
        _fail("PROVIDER is set to 'openai' but OPENAI_API_KEY is missing from .env.")

    if not provider:
        # Auto-detect: prefer the free option.
        if gemini_key:
            provider = "gemini"
        elif openai_key:
            provider = "openai"
        else:
            print("ERROR: No API key found in your .env file.")
            print()
            print("Easiest fix — Google Gemini is FREE (no credit card needed):")
            print("  1. Get a key at https://aistudio.google.com/apikey")
            print("  2. Copy .env.example to .env")
            print("  3. Put your key in it:  GEMINI_API_KEY=your-key-here")
            print()
            print("Prefer OpenAI? Get a key at https://platform.openai.com/api-keys")
            print("and set OPENAI_API_KEY instead (pay-per-use).")
            print()
            print("(.env is gitignored, so your key stays out of GitHub.)")
            sys.exit(1)

    default_model = (
        DEFAULT_GEMINI_MODEL if provider == "gemini" else DEFAULT_OPENAI_MODEL
    )
    model_env = "GEMINI_MODEL" if provider == "gemini" else "OPENAI_MODEL"
    model = os.environ.get(model_env, "").strip() or default_model

    return {
        "provider": provider,
        "gemini_key": gemini_key,
        "openai_key": openai_key,
        "model": model,
        "system_prompt": (
            os.environ.get("CHATBOT_SYSTEM_PROMPT", "").strip()
            or DEFAULT_SYSTEM_PROMPT
        ),
    }


def make_backend(config: dict):
    """Create the AI client for the chosen provider."""
    if config["provider"] == "gemini":
        return GeminiBackend(
            config["gemini_key"], config["model"], config["system_prompt"]
        )
    return OpenAIBackend(
        config["openai_key"], config["model"], config["system_prompt"]
    )


# --- Main loop ----------------------------------------------------------------

def main() -> None:
    config = load_config()
    backend = make_backend(config)
    provider_label = PROVIDER_LABELS[config["provider"]]
    model = config["model"]

    print("=" * 60)
    print("  TDL Chatbot")
    print(f"  AI: {provider_label} — {model}")
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
            print(f"Currently using: {provider_label} ({model})")
            continue

        history.append({"role": "user", "content": user_input})

        try:
            print("\nTDL Bot: ", end="", flush=True)
            reply = backend.reply(history)
            print(reply)
        except ChatbotError as exc:
            print(exc)
            history.pop()  # drop the failed turn so history stays clean
        else:
            history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
