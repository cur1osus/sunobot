from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiogram import Bot

from bot.db.enum import UsageEventType
from bot.scheduler import CancelJob, default_scheduler
from bot.utils.background_task_helpers import _refund_credits, _send_tracks
from bot.utils.suno_api import SunoAPIError, build_suno_client
from bot.utils.usage_events import record_usage_event_by_user_id

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    user_id: int,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
    credits_cost: int,
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
        user_id=user_id,
        sessionmaker=sessionmaker,
        redis=redis,
        credits_cost=credits_cost,
    )


async def _poll_music_task(
    *,
    bot: Bot,
    chat_id: int,
    task_id: str,
    filename_base: str,
    context: MusicTaskContext,
    poll_timeout: int,
    user_id: int,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
    credits_cost: int,
) -> CancelJob | None:
    if time.monotonic() - context.started_at > poll_timeout:
        if context.timeout_extensions < MAX_TIMEOUT_EXTENSIONS:
            context.timeout_extensions += 1
            context.started_at = time.monotonic()
            logger.warning(
                "Ожидание по задаче %s истекло, продлеваю (%s/%s)",
                task_id,
                context.timeout_extensions,
                MAX_TIMEOUT_EXTENSIONS,
            )
            return None
        logger.warning("Ожидание по задаче %s истекло", task_id)
        await _refund_credits(
            sessionmaker=sessionmaker,
            redis=redis,
            user_id=user_id,
            amount=credits_cost,
        )
        await bot.send_message(chat_id, "Генерация превысила лимит ожидания.")
        return CancelJob

    client = build_suno_client()
    try:
        details = await client.get_task_details(task_id)
    except SunoAPIError as err:
        context.errors += 1
        logger.warning("Не удалось опросить задачу %s: %s", task_id, err)
        if context.errors >= MAX_POLL_ERRORS:
            await _refund_credits(
                sessionmaker=sessionmaker,
                redis=redis,
                user_id=user_id,
                amount=credits_cost,
            )
            await bot.send_message(
                chat_id,
                "Не удалось получить результат генерации. Попробуйте позже.",
            )
            return CancelJob
        return None

    data = details.get("data", {}) or {}
    status = str(data.get("status") or "").upper()

    if status == "SUCCESS":
        sent_any = await _send_tracks(bot, chat_id, filename_base, data)
        if sent_any:
            await record_usage_event_by_user_id(
                sessionmaker=sessionmaker,
                user_id=user_id,
                event_type=UsageEventType.SONG.value,
            )
        return CancelJob

    if status in TERMINAL_STATUSES:
        logger.warning("Задача %s завершилась со статусом %s", task_id, status)
        await _refund_credits(
            sessionmaker=sessionmaker,
            redis=redis,
            user_id=user_id,
            amount=credits_cost,
        )
        await bot.send_message(
            chat_id,
            STATUS_MESSAGES.get(status, "Генерация завершилась с ошибкой."),
        )
        return CancelJob

    return None
