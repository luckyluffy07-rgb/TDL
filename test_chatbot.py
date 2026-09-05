"""Offline tests for chatbot.py — no API key or network needed.

Run with:
    python -m unittest test_chatbot.py -v
"""

import unittest
from unittest import mock

import chatbot
from chatbot import ChatbotError, GeminiBackend, OpenAIBackend


# --- Fakes for the Google Gemini SDK -----------------------------------------

class FakeGeminiErrors:
    class ClientError(Exception):
        def __init__(self, code, message=""):
            super().__init__(message)
            self.code = code
            self.message = message

    class ServerError(Exception):
        def __init__(self, code=500, message=""):
            super().__init__(message)
            self.code = code
            self.message = message


class FakeGenerateContentConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeGeminiModels:
    """Stand-in for client.models — records calls, returns a canned reply."""

    def __init__(self, text="Hello from fake Gemini!", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        response = mock.Mock()
        response.text = self.text
        return response


class FakeGeminiClient:
    def __init__(self, models):
        self.models = models


class FakeGeminiModule:
    """Stand-in for the google.genai module."""

    def __init__(self, client):
        self._client = client

    def Client(self, api_key=None):  # capital C mirrors the real SDK
        return self._client


def patch_gemini(models):
    """Point chatbot's _import_gemini at our fakes (use as a context manager)."""
    fake_module = FakeGeminiModule(FakeGeminiClient(models))
    fake_types = mock.Mock()
    fake_types.GenerateContentConfig = FakeGenerateContentConfig
    return mock.patch.object(
        chatbot,
        "_import_gemini",
        return_value=(fake_module, fake_types, FakeGeminiErrors),
    )


# --- Fakes for the OpenAI SDK -------------------------------------------------

class FakeAuthError(Exception):
    pass


class FakeRateLimitError(Exception):
    pass


class FakeConnectionError(Exception):
    pass


class FakeStatusError(Exception):
    def __init__(self, status_code, message=""):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class FakeResponses:
    def __init__(self, text="Hello from fake GPT!", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        response = mock.Mock()
        response.output_text = self.text
        return response


def patch_openai(responses):
    """Point chatbot's _import_openai at our fakes (use as a context manager)."""
    client = mock.Mock()
    client.responses = responses

    def fake_client_class(api_key=None):
        return client

    return mock.patch.object(
        chatbot,
        "_import_openai",
        return_value=(
            fake_client_class,
            FakeAuthError,
            FakeRateLimitError,
            FakeConnectionError,
            FakeStatusError,
        ),
    )


# --- GeminiBackend ------------------------------------------------------------

class GeminiBackendTests(unittest.TestCase):
    def make_backend(self, models):
        with patch_gemini(models):
            backend = GeminiBackend("fake-key", "gemini-test", "Be nice.")
        return backend

    def test_reply_returns_text_and_converts_roles(self):
        models = FakeGeminiModels("Hi from Gemini!")
        backend = self.make_backend(models)

        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi!"},
            {"role": "user", "content": "how are you?"},
        ]
        self.assertEqual(backend.reply(history), "Hi from Gemini!")

        call = models.calls[0]
        self.assertEqual(call["model"], "gemini-test")
        self.assertEqual(call["config"].kwargs["system_instruction"], "Be nice.")
        # Gemini wants "model" instead of "assistant", and text inside "parts"
        self.assertEqual(
            call["contents"],
            [
                {"role": "user", "parts": [{"text": "hello"}]},
                {"role": "model", "parts": [{"text": "hi!"}]},
                {"role": "user", "parts": [{"text": "how are you?"}]},
            ],
        )

    def test_rate_limit_becomes_friendly_error(self):
        models = FakeGeminiModels(error=FakeGeminiErrors.ClientError(429, "slow down"))
        backend = self.make_backend(models)
        with self.assertRaises(ChatbotError) as ctx:
            backend.reply([{"role": "user", "content": "hi"}])
        self.assertIn("rate limit", str(ctx.exception).lower())

    def test_bad_key_becomes_friendly_error(self):
        models = FakeGeminiModels(error=FakeGeminiErrors.ClientError(403, "denied"))
        backend = self.make_backend(models)
        with self.assertRaises(ChatbotError) as ctx:
            backend.reply([{"role": "user", "content": "hi"}])
        self.assertIn("api key", str(ctx.exception).lower())

    def test_empty_reply_becomes_friendly_error(self):
        models = FakeGeminiModels(text="")
        backend = self.make_backend(models)
        with self.assertRaises(ChatbotError):
            backend.reply([{"role": "user", "content": "hi"}])


# --- OpenAIBackend ------------------------------------------------------------

class OpenAIBackendTests(unittest.TestCase):
    def make_backend(self, responses):
        with patch_openai(responses):
            backend = OpenAIBackend("fake-key", "gpt-test", "Be nice.")
        return backend

    def test_reply_returns_output_text(self):
        responses = FakeResponses("Hi there!")
        backend = self.make_backend(responses)
        history = [{"role": "user", "content": "hello"}]
        self.assertEqual(backend.reply(history), "Hi there!")

    def test_sends_model_instructions_and_full_history(self):
        responses = FakeResponses()
        backend = self.make_backend(responses)
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello!"},
            {"role": "user", "content": "how are you?"},
        ]
        backend.reply(history)

        call = responses.calls[0]
        self.assertEqual(call["model"], "gpt-test")
        self.assertEqual(call["instructions"], "Be nice.")
        self.assertEqual(call["input"], history)

    def test_auth_error_becomes_friendly_error(self):
        responses = FakeResponses(error=FakeAuthError("401"))
        backend = self.make_backend(responses)
        with self.assertRaises(ChatbotError) as ctx:
            backend.reply([{"role": "user", "content": "hi"}])
        self.assertIn("api key", str(ctx.exception).lower())


# --- Provider selection -------------------------------------------------------

def env_with(**overrides):
    env = {"GEMINI_API_KEY": "", "OPENAI_API_KEY": "", "PROVIDER": "",
           "GEMINI_MODEL": "", "OPENAI_MODEL": "", "CHATBOT_SYSTEM_PROMPT": ""}
    env.update(overrides)
    return mock.patch.dict(chatbot.os.environ, env, clear=True)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        # Never read the developer's real .env during tests
        patcher = mock.patch.object(chatbot, "load_dotenv", lambda: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_key_at_all_exits_with_error(self):
        with env_with():
            with self.assertRaises(SystemExit) as ctx:
                chatbot.load_config()
        self.assertEqual(ctx.exception.code, 1)

    def test_gemini_key_only_uses_gemini_with_default_model(self):
        with env_with(GEMINI_API_KEY="AIza-fake"):
            config = chatbot.load_config()
        self.assertEqual(config["provider"], "gemini")
        self.assertEqual(config["model"], chatbot.DEFAULT_GEMINI_MODEL)

    def test_openai_key_only_uses_openai_with_default_model(self):
        with env_with(OPENAI_API_KEY="sk-fake"):
            config = chatbot.load_config()
        self.assertEqual(config["provider"], "openai")
        self.assertEqual(config["model"], chatbot.DEFAULT_OPENAI_MODEL)

    def test_gemini_wins_when_both_keys_present(self):
        with env_with(GEMINI_API_KEY="AIza-fake", OPENAI_API_KEY="sk-fake"):
            config = chatbot.load_config()
        self.assertEqual(config["provider"], "gemini")

    def test_provider_openai_overrides_gemini(self):
        with env_with(GEMINI_API_KEY="AIza-fake", OPENAI_API_KEY="sk-fake",
                      PROVIDER="openai"):
            config = chatbot.load_config()
        self.assertEqual(config["provider"], "openai")

    def test_provider_openai_without_openai_key_fails(self):
        with env_with(GEMINI_API_KEY="AIza-fake", PROVIDER="openai"):
            with self.assertRaises(SystemExit):
                chatbot.load_config()

    def test_unknown_provider_fails(self):
        with env_with(GEMINI_API_KEY="AIza-fake", PROVIDER="claude"):
            with self.assertRaises(SystemExit):
                chatbot.load_config()


if __name__ == "__main__":
    unittest.main()
