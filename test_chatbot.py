"""Offline tests for chatbot.py — no API key or network needed.

Run with:
    python -m unittest test_chatbot.py -v
"""

import unittest
from unittest import mock

import chatbot


class FakeResponses:
    """A stand-in for client.responses that records calls and returns a canned reply."""

    def __init__(self, text="Hello from the fake model!"):
        self.text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = mock.Mock()
        response.output_text = self.text
        return response


def make_client(text="Hello from the fake model!"):
    client = mock.Mock()
    client.responses = FakeResponses(text)
    return client


class GetReplyTests(unittest.TestCase):
    def test_returns_the_models_reply_text(self):
        client = make_client("Hi there!")
        reply = chatbot.get_reply(
            client,
            model="gpt-test",
            system_prompt="Be nice.",
            history=[{"role": "user", "content": "hello"}],
        )
        self.assertEqual(reply, "Hi there!")

    def test_sends_model_instructions_and_full_history(self):
        client = make_client()
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello!"},
            {"role": "user", "content": "how are you?"},
        ]
        chatbot.get_reply(
            client, model="gpt-test", system_prompt="Be nice.", history=history
        )

        call = client.responses.calls[0]
        self.assertEqual(call["model"], "gpt-test")
        self.assertEqual(call["instructions"], "Be nice.")
        self.assertEqual(call["input"], history)


class ConfigTests(unittest.TestCase):
    def test_no_api_key_exits_with_error(self):
        env = {"OPENAI_API_KEY": "", "OPENAI_MODEL": "", "CHATBOT_SYSTEM_PROMPT": ""}
        with mock.patch.dict(chatbot.os.environ, env, clear=True), \
                mock.patch.object(chatbot, "load_dotenv", lambda: None):
            with self.assertRaises(SystemExit) as ctx:
                chatbot.load_config()
        self.assertEqual(ctx.exception.code, 1)

    def test_model_falls_back_to_default_when_not_set(self):
        env = {"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": ""}
        with mock.patch.dict(chatbot.os.environ, env, clear=True), \
                mock.patch.object(chatbot, "load_dotenv", lambda: None):
            config = chatbot.load_config()
        self.assertEqual(config["model"], chatbot.DEFAULT_MODEL)


if __name__ == "__main__":
    unittest.main()
