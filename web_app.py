#!/usr/bin/env python3
"""
TDL Chatbot — web version.

A small Flask server that puts the same chatbot from chatbot.py behind a
browser UI. It reuses the Gemini/OpenAI backends, so your .env settings
work exactly the same way.

Usage:
    pip install -r requirements.txt
    python web_app.py
    # then open http://localhost:5000

Conversation history lives in the browser and is sent with each request,
so the server stays stateless and you can run several chats at once.
"""

import os

from flask import Flask, jsonify, request, send_from_directory

from chatbot import (
    PROVIDER_LABELS,
    ChatbotError,
    load_config,
    make_backend,
)

MAX_HISTORY_MESSAGES = 40  # keep requests (and token bills) sensible

app = Flask(__name__, static_folder="static", static_url_path="")

_config = None
_backend = None


def get_backend():
    """Create the AI backend once, on first use."""
    global _config, _backend
    if _backend is None:
        _config = load_config()
        _backend = make_backend(_config)
    return _config, _backend


def _clean_history(raw) -> list[dict]:
    """Validate the history the browser sent us."""
    if not isinstance(raw, list):
        raise ChatbotError("Malformed request: 'messages' must be a list.")

    history = []
    for message in raw[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            history.append({"role": role, "content": content.strip()})

    if not history:
        raise ChatbotError("Say something first!")
    if history[-1]["role"] != "user":
        raise ChatbotError("The last message must come from you.")
    return history


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/info")
def info():
    """Which provider/model the UI is talking to."""
    try:
        config, _ = get_backend()
    except ChatbotError as exc:
        return jsonify({"error": str(exc)}), 500
    except SystemExit:
        return jsonify({"error": "No API key configured — see .env.example."}), 500
    return jsonify(
        {
            "provider": PROVIDER_LABELS[config["provider"]],
            "model": config["model"],
        }
    )


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    try:
        history = _clean_history(payload.get("messages"))
        _, backend = get_backend()
        reply = backend.reply(history)
    except ChatbotError as exc:
        return jsonify({"error": str(exc)}), 400
    except SystemExit:
        return jsonify({"error": "No API key configured — see .env.example."}), 500
    except Exception as exc:  # last-resort safety net
        return jsonify({"error": f"⚠️ Unexpected error: {exc}"}), 500
    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # 0.0.0.0 so it also works inside containers / remote dev boxes.
    app.run(host="0.0.0.0", port=port, debug=False)
