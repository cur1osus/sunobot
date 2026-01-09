from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from bot.settings import se


class SunoAPIError(Exception):
    """Errors returned from the Suno API."""


class SunoClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.sunoapi.org",
        callback_url: str,
        default_model: str = "V5",
        poll_interval: float = 10,
        poll_timeout: int = 300,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.callback_url = callback_url
        self.default_model = default_model
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                timeout=self.poll_timeout,
            ) as response:
                payload: dict[str, Any] = await response.json()

                if response.status >= 400:
                    raise SunoAPIError(
                        payload.get("msg")
                        or f"Suno API error {response.status}: {payload}"
                    )

                code = payload.get("code", 200)
                if code != 200:
                    raise SunoAPIError(
                        payload.get("msg", f"Suno API returned code {code}")
                    )

                return payload

    async def generate_music(
        self,
        *,
        prompt: str,
        custom_mode: bool,
        instrumental: bool,
        style: str = "",
        title: str = "",
        model: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "style": style,
            "title": title,
            "customMode": custom_mode,
            "instrumental": instrumental,
            "callBackUrl": self.callback_url,
            "model": model or self.default_model,
        }

        data = await self._request(
            "POST",
            "/api/v1/generate",
            json=payload,
        )
        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            raise SunoAPIError("Не удалось получить taskId из ответа Suno API.")
        return task_id

    async def generate_lyrics(
        self,
        *,
        prompt: str,
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "callBackUrl": self.callback_url,
        }

        data = await self._request(
            "POST",
            "/api/v1/lyrics",
            json=payload,
        )

        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            raise SunoAPIError("Не удалось получить taskId из ответа Suno API.")

        status, details = await self.poll_lyrics(task_id)
        if status != "SUCCESS":
            raise SunoAPIError(f"Генерация текста завершилась со статусом: {status}")

        response = details.get("response", {}) or {}
        items = response.get("data") or []
        for item in items:
            if isinstance(item, dict) and item.get("text"):
                return str(item["text"])

        raise SunoAPIError("Не удалось получить текст песни из ответа Suno API.")

    async def get_task_details(self, task_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/generate/record-info",
            params={"taskId": task_id},
        )

    async def get_remaining_credits(self) -> int:
        data = await self._request(
            "GET",
            "/api/v1/generate/credit",
        )
        credits = data.get("data")
        if credits is None:
            raise SunoAPIError("Не удалось получить баланс кредитов из Suno API.")
        return int(credits)

    async def get_lyrics_details(self, task_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/lyrics/record-info",
            params={"taskId": task_id},
        )

    async def poll_task(self, task_id: str) -> tuple[str, dict[str, Any]]:
        deadline = asyncio.get_event_loop().time() + self.poll_timeout
        terminal_statuses = {
            "SUCCESS",
            "CREATE_TASK_FAILED",
            "GENERATE_AUDIO_FAILED",
            "CALLBACK_EXCEPTION",
            "SENSITIVE_WORD_ERROR",
        }

        details: dict[str, Any] = {}
        while asyncio.get_event_loop().time() < deadline:
            details = await self.get_task_details(task_id)
            data = details.get("data", {}) or {}
            status = str(data.get("status") or "").upper()

            if status in terminal_statuses:
                return status, data

            await asyncio.sleep(self.poll_interval)

        return "TIMEOUT", details.get("data", {}) if details else {}

    async def poll_lyrics(self, task_id: str) -> tuple[str, dict[str, Any]]:
        deadline = asyncio.get_event_loop().time() + self.poll_timeout
        terminal_statuses = {
            "SUCCESS",
            "CREATE_TASK_FAILED",
            "GENERATE_LYRICS_FAILED",
            "CALLBACK_EXCEPTION",
            "SENSITIVE_WORD_ERROR",
        }

        details: dict[str, Any] = {}
        while asyncio.get_event_loop().time() < deadline:
            details = await self.get_lyrics_details(task_id)
            data = details.get("data", {}) or {}
            status = str(data.get("status") or "").upper()

            if status in terminal_statuses:
                return status, data

            await asyncio.sleep(self.poll_interval)

        return "TIMEOUT", details.get("data", {}) if details else {}


def build_suno_client() -> SunoClient:
    return SunoClient(
        api_key=se.suno.api_key,
        callback_url=se.suno.callback_url,
        default_model=se.suno.model,
        poll_interval=se.suno.poll_interval,
        poll_timeout=se.suno.poll_timeout,
    )
