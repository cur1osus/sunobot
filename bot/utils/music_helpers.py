from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.background_tasks import schedule_music_task
from bot.db.func import charge_user_credits, refund_user_credits
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.inline import ik_back_home, ik_main
from bot.states import MusicGenerationState
from bot.utils.agent_platform import build_agent_platform_client
from bot.utils.music_state import get_music_data, update_music_data
from bot.utils.suno_api import SunoAPIError, build_suno_client
from bot.utils.texts import MUSIC_TITLE_TEXT

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from bot.db.redis.user_model import UserRD
    from bot.utils.agent_platform import AgentPlatformClient
    from bot.utils.suno_api import SunoClient


logger = logging.getLogger(__name__)

MAX_QUICK_PROMPT_LEN = 500


def _client() -> SunoClient:
    return build_suno_client()


def _lyrics_client() -> AgentPlatformClient:
    return build_agent_platform_client()


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


async def ask_for_title(state: FSMContext, message: Message) -> None:
    await state.set_state(MusicGenerationState.title)
    await message.answer(
        MUSIC_TITLE_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
    )


async def start_generation(
    message: Message,
    state: FSMContext,
    *,
    user: UserRD,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
) -> None:
    client = _client()
    data = await get_music_data(state)
    custom_mode = data.custom_mode
    instrumental = data.instrumental
    prompt = data.prompt
    generation_prompt = prompt
    style = data.style if custom_mode else ""
    title = data.title if custom_mode else ""

    if not generation_prompt:
        await message.answer("Промпт не задан.")
        return

    if not custom_mode and prompt and len(prompt) > MAX_QUICK_PROMPT_LEN:
        generation_prompt = prompt[:MAX_QUICK_PROMPT_LEN].rstrip()
        await update_music_data(state, prompt=generation_prompt)
        await message.answer(
            "Текст превышает 500 символов, обрезал для быстрого режима."
        )

    credits_cost = 2
    if not await charge_user_credits(
        session=session,
        redis=redis,
        user=user,
        amount=credits_cost,
    ):
        await message.answer(
            "Недостаточно кредитов для генерации музыки. Нужно 2 кредита."
        )
        await state.clear()
        return

    await state.set_state(MusicGenerationState.waiting)
    await message.answer("Запускаю генерацию музыки в Suno...")

    try:
        task_id = await client.generate_music(
            prompt=generation_prompt,
            custom_mode=custom_mode,
            instrumental=instrumental,
            style=style,
            title=title,
        )
    except SunoAPIError as err:
        logger.warning("Не удалось запустить генерацию музыки: %s", err)
        await refund_user_credits(
            session=session,
            redis=redis,
            user=user,
            amount=credits_cost,
        )
        await message.answer("Не удалось запустить генерацию музыки. Попробуйте позже.")
        await state.clear()
        return

    base_name = title.strip() if title.strip() else _first_line(prompt)
    if not base_name:
        base_name = "Трек"

    schedule_music_task(
        bot=message.bot,
        chat_id=message.chat.id,
        task_id=task_id,
        filename_base=base_name,
        poll_interval=client.poll_interval,
        poll_timeout=client.poll_timeout,
        user_id=user.user_id,
        sessionmaker=sessionmaker,
        redis=redis,
        credits_cost=credits_cost,
    )

    await message.answer(
        f"Задача {task_id} создана. Я пришлю файл, когда трек будет готов.",
        reply_markup=await ik_main(),
    )
    await state.clear()
