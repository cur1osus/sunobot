from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from bot.utils.suno_api import SunoClient

pytestmark = pytest.mark.asyncio


async def test_generate_music_payload(monkeypatch) -> None:
    client = SunoClient(
        api_key="key",
        base_url="https://example.test",
        callback_url="https://callback",
        default_model="V5",
        poll_interval=1,
        poll_timeout=2,
    )

    captured = {}

    async def fake_request(method, path, *, payload=None, params=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = payload
        captured["params"] = params
        return {"data": {"taskId": "task"}}

    monkeypatch.setattr(client, "_request", AsyncMock(side_effect=fake_request))

    task_id = await client.generate_music(
        prompt="prompt",
        custom_mode=True,
        instrumental=False,
        style="rock",
        title="title",
        model="V5",
    )

    assert task_id == "task"
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/generate"
    payload = captured["json"]
    assert payload["prompt"] == "prompt"
    assert payload["customMode"] is True
    assert payload["instrumental"] is False
    assert payload["style"] == "rock"
    assert payload["title"] == "title"


async def test_get_task_details_request(monkeypatch) -> None:
    client = SunoClient(
        api_key="key",
        base_url="https://example.test",
        callback_url="https://callback",
        default_model="V5",
        poll_interval=1,
        poll_timeout=2,
    )

    async def fake_request(method, path, *, payload=None, params=None):
        assert method == "GET"
        assert path == "/api/v1/generate/record-info"
        assert params == {"taskId": "id"}
        return {"data": {"status": "SUCCESS"}}

    monkeypatch.setattr(client, "_request", AsyncMock(side_effect=fake_request))

    data = await client.get_task_details("id")
    assert data["data"]["status"] == "SUCCESS"
