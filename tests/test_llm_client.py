
from types import SimpleNamespace

import pytest

from llm.config import LLMSettings, load_settings
from llm.gemini_client import GeminiModelClient


def make_settings(**overrides):
    values = {
        "provider": "gemini",
        "model": "test-model",
        "api_key": "test-key",
        "timeout_seconds": 10,
        "max_retries": 0,
        "max_output_tokens": 500,
    }
    values.update(overrides)
    return LLMSettings(**values)


class FakeModels:
    def __init__(self, text="Architecture recommendation"):
        self.text = text
        self.kwargs = None

    async def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text=self.text)


class FakeAio:
    def __init__(self, text="Architecture recommendation"):
        self.models = FakeModels(text)
        self.closed = False

    async def aclose(self):
        self.closed = True


class FakeClient:
    def __init__(self, text="Architecture recommendation"):
        self.aio = FakeAio(text)


@pytest.mark.asyncio
async def test_gemini_client_returns_generated_text():
    fake = FakeClient()
    client = GeminiModelClient(
        settings=make_settings(),
        client=fake,
    )

    result = await client.generate_text(
        system_prompt="You are a software architect.",
        user_prompt="Design a URL shortener.",
    )

    assert result == "Architecture recommendation"
    assert fake.aio.models.kwargs["model"] == "test-model"


@pytest.mark.asyncio
async def test_gemini_client_rejects_empty_response():
    client = GeminiModelClient(
        settings=make_settings(),
        client=FakeClient(text="   "),
    )

    with pytest.raises(ValueError, match="empty text response"):
        await client.generate_text(
            system_prompt="You are an architect.",
            user_prompt="Design a URL shortener.",
        )


def test_gemini_client_requires_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiModelClient(
            settings=make_settings(api_key=None)
        )



def test_mock_mode_is_the_default(monkeypatch):
    import llm.config as config

    # Prevent the project's .env file from influencing this test.
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    settings = config.load_settings()

    assert settings.provider == "mock"