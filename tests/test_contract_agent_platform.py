from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot.utils.agent_platform import SONG_PROMPT_SUFFIX, AgentPlatformClient


class _FakeResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return {"choices": [{"message": {"content": "TEXT"}}]}


class _FakeSession:
    def __init__(self, holder: dict[str, object]) -> None:
        self._holder = holder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *, url, headers, json):
        self._holder["url"] = url
        self._holder["headers"] = headers
        self._holder["json"] = json
        return _FakeResponse()


@pytest.mark.asyncio
async def test_generate_song_text_builds_prompt(monkeypatch) -> None:
    holder: dict[str, object] = {}
    monkeypatch.setattr(
        "bot.utils.agent_platform.aiohttp.ClientSession",
        lambda *args, **kwargs: _FakeSession(holder),
    )
    client = AgentPlatformClient(
        api_key="key",
        base_url="https://example.test/v1",
        model="model",
        timeout=1,
    )

    result = await client.generate_song_text(prompt="Тема")

    assert result == "TEXT"
    payload = holder["json"]
    assert payload["model"] == "model"
    content = payload["messages"][0]["content"]
    assert SONG_PROMPT_SUFFIX in content
    assert content.startswith("Тема")


def test_chat_url_suffix() -> None:
    client = AgentPlatformClient(
        api_key="key",
        base_url="https://example.test/v1",
        model="model",
        timeout=1,
    )
    assert client._chat_url().endswith("/chat/completions")

    client = AgentPlatformClient(
        api_key="key",
        base_url="https://example.test/v1/chat/completions",
        model="model",
        timeout=1,
    )
    assert client._chat_url() == "https://example.test/v1/chat/completions"
