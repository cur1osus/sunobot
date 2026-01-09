from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.keyboards.inline import ik_main
from bot.scheduler import CancelJob, default_scheduler
from bot.utils.suno_api import SunoAPIError, build_suno_client

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {
    "SUCCESS",
    "CREATE_TASK_FAILED",
    "GENERATE_AUDIO_FAILED",
    "CALLBACK_EXCEPTION",
    "SENSITIVE_WORD_ERROR",
}
STATUS_MESSAGES = {
    "CREATE_TASK_FAILED": "Не удалось создать задачу генерации.",
    "GENERATE_AUDIO_FAILED": "Не удалось сгенерировать аудио.",
    "CALLBACK_EXCEPTION": "Произошла ошибка при обработке результата.",
    "SENSITIVE_WORD_ERROR": "В тексте обнаружены запрещенные слова.",
}
MAX_POLL_ERRORS = 3
FILENAME_LIMIT = 80
MIN_POLL_TIMEOUT = 600
MAX_TIMEOUT_EXTENSIONS = 2


@dataclass
class MusicTaskContext:
    started_at: float
    errors: int = 0
    timeout_extensions: int = 0


def schedule_music_task(
    *,
    bot: Bot,
    chat_id: int,
    task_id: str,
    filename_base: str,
    poll_interval: float,
    poll_timeout: int,
) -> None:
    interval_seconds = max(1, int(round(poll_interval)))
    effective_timeout = max(poll_timeout, MIN_POLL_TIMEOUT)
    context = MusicTaskContext(started_at=time.monotonic())
    default_scheduler.every(interval_seconds).seconds.do(
        _poll_music_task,
        bot=bot,
        chat_id=chat_id,
        task_id=task_id,
        filename_base=filename_base,
        context=context,
        poll_timeout=effective_timeout,
    )


async def _poll_music_task(
    *,
    bot: Bot,
    chat_id: int,
    task_id: str,
    filename_base: str,
    context: MusicTaskContext,
    poll_timeout: int,
) -> CancelJob | None:
    if time.monotonic() - context.started_at > poll_timeout:
        if context.timeout_extensions < MAX_TIMEOUT_EXTENSIONS:
            context.timeout_extensions += 1
            context.started_at = time.monotonic()
            logger.warning(
                "Polling timed out for task %s, extending wait (%s/%s)",
                task_id,
                context.timeout_extensions,
                MAX_TIMEOUT_EXTENSIONS,
            )
            return None
        logger.warning("Polling timed out for task %s", task_id)
        await bot.send_message(chat_id, "Генерация превысила лимит ожидания.")
        return CancelJob

    client = build_suno_client()
    try:
        details = await client.get_task_details(task_id)
    except SunoAPIError as err:
        context.errors += 1
        logger.warning("Failed to poll task %s: %s", task_id, err)
        if context.errors >= MAX_POLL_ERRORS:
            await bot.send_message(
                chat_id,
                "Не удалось получить результат генерации. Попробуйте позже.",
            )
            return CancelJob
        return None

    data = details.get("data", {}) or {}
    status = str(data.get("status") or "").upper()

    if status == "SUCCESS":
        await _send_tracks(bot, chat_id, filename_base, data)
        return CancelJob

    if status in TERMINAL_STATUSES:
        logger.warning("Task %s завершилась со статусом %s", task_id, status)
        await bot.send_message(
            chat_id,
            STATUS_MESSAGES.get(status, "Генерация завершилась с ошибкой."),
        )
        return CancelJob

    return None


async def _send_tracks(
    bot: Bot,
    chat_id: int,
    filename_base: str,
    data: dict[str, Any],
) -> None:
    response = data.get("response", {}) if isinstance(data, dict) else {}
    tracks = response.get("sunoData") or []
    if not tracks:
        logger.warning("No tracks returned for filename base %s", filename_base)
        await bot.send_message(chat_id, "Готово, но ссылки на аудио не получены.")
        return

    total = len(tracks)
    sent_any = False
    for idx, track in enumerate(tracks, start=1):
        audio_url = track.get("audioUrl") or track.get("streamAudioUrl")
        if not audio_url:
            continue

        try:
            audio_bytes = await _download_audio(audio_url)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            logger.warning("Failed to download audio for %s: %s", audio_url, err)
            await bot.send_message(
                chat_id,
                f"Не удалось скачать аудио для трека {idx}.",
            )
            continue

        filename = _build_filename(filename_base, idx, total, audio_url)
        try:
            await bot.send_audio(
                chat_id=chat_id,
                audio=BufferedInputFile(audio_bytes, filename=filename),
            )
            sent_any = True
        except Exception as err:
            logger.warning("Failed to send audio file %s: %s", filename, err)
            await bot.send_message(
                chat_id,
                f"Не удалось отправить файл для трека {idx}.",
            )

    if sent_any:
        await bot.send_message(
            chat_id,
            "Готово! Открой меню, чтобы запустить новую задачу.",
            reply_markup=await ik_main(),
        )
    else:
        logger.warning("No audio files were sent for filename base %s", filename_base)
        await bot.send_message(chat_id, "Не удалось отправить ни одного файла.")


async def _download_audio(url: str) -> bytes:
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()


def _build_filename(base: str, index: int, total: int, url: str) -> str:
    base_name = _sanitize_filename(base) or "track"
    suffix = Path(urlparse(url).path).suffix or ".mp3"
    if total > 1:
        return f"{base_name}_{index}{suffix}"
    return f"{base_name}{suffix}"


def _sanitize_filename(name: str) -> str:
    cleaned = "".join(ch if ch not in '\\/:*?"<>|\n\r\t' else "_" for ch in name)
    cleaned = " ".join(cleaned.split()).strip().rstrip(".")
    if len(cleaned) > FILENAME_LIMIT:
        cleaned = cleaned[:FILENAME_LIMIT].rstrip()
    return cleaned
