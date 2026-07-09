import pytest
from pydantic import BaseModel

from tests._support import ensure_package, load_module

ensure_package("onecrawler")
ensure_package("onecrawler.crawler")
ensure_package("onecrawler.crawler.scraper")
ensure_package("onecrawler.crawler.scraper.genai")

model_module = load_module(
    "onecrawler.crawler.scraper.genai.model",
    "onecrawler/crawler/scraper/genai/model.py",
)


class Output(BaseModel):
    title: str


class FakeLLM:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        FakeLLM.instances.append(self)

    async def generate(self, prompt, schema=None):
        self.calls.append((prompt, schema))
        return {"prompt": prompt, "schema": schema}

    async def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def reset_fake_llm():
    FakeLLM.instances = []


@pytest.mark.asyncio
async def test_llm_manager_uses_custom_provider_and_forwards_schema(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAILLM", FakeLLM)

    manager = model_module.LLMManager(
        schema=Output,
        model_provider="openai",
        model_name="test-model",
        api_key="test-key",
    )

    result = await manager.generate("extract this")

    assert isinstance(manager.model, FakeLLM)
    assert manager.model.kwargs == {
        "api_key": "test-key",
        "model": "test-model",
        "base_url": "https://api.openai.com/v1",
    }
    assert manager.model.calls == [("extract this", Output)]
    assert result == {"prompt": "extract this", "schema": Output}


def test_llm_manager_supports_google_alias(monkeypatch):
    monkeypatch.setattr(model_module, "GeminiLLM", FakeLLM)

    manager = model_module.LLMManager(
        schema=Output,
        model_provider="google",
        model_name="gemini-test",
        base_url="https://example.test",
        api_key="test-key",
    )

    assert manager.model.kwargs == {
        "api_key": "test-key",
        "model": "gemini-test",
        "base_url": "https://example.test",
    }


def test_llm_manager_rejects_missing_api_key():
    with pytest.raises(ValueError, match="api_key is required"):
        model_module.LLMManager(
            schema=Output,
            model_provider="openai",
            model_name="test-model",
        )


def test_llm_manager_openai_allows_missing_key_with_custom_base_url(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAILLM", FakeLLM)

    manager = model_module.LLMManager(
        schema=Output,
        model_provider="openai",
        model_name="local-model",
        base_url="http://localhost:8080/v1",
    )

    assert manager.model.kwargs == {
        "api_key": None,
        "model": "local-model",
        "base_url": "http://localhost:8080/v1",
    }


@pytest.mark.asyncio
async def test_openai_llm_sends_auth_header_only_when_keyed():
    # model.py's `from .llms import OpenAILLM` already loaded the real class.
    OpenAILLM = model_module.OpenAILLM
    keyed = OpenAILLM(api_key="sk-abc", base_url="http://x/v1")
    keyless = OpenAILLM(base_url="http://localhost:8080/v1")
    try:
        keyed_headers = {k.lower() for k in keyed.client.headers}
        keyless_headers = {k.lower() for k in keyless.client.headers}
        assert "authorization" in keyed_headers
        assert "authorization" not in keyless_headers
    finally:
        await keyed.close()
        await keyless.close()
