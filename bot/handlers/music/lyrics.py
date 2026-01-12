from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.enum import UsageEventType
from bot.db.func import charge_user_credits, refund_user_credits
from bot.db.redis.user_model import UserRD
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicTextAction
from bot.keyboards.inline import ik_back_home, ik_music_text_menu
from bot.states import MusicGenerationState
from bot.utils.agent_platform import AgentPlatformAPIError
from bot.utils.messaging import edit_or_answer
from bot.utils.music_helpers import _lyrics_client, ask_for_title  # noqa: PLC2701
from bot.utils.music_state import get_music_data, update_music_data
from bot.utils.texts import (
    LYRICS_MENU_TEXT,
    MUSIC_PROMPT_AI_TEXT,
    MUSIC_PROMPT_INSTRUMENTAL_TEXT,
    MUSIC_PROMPT_MANUAL_TEXT,
)
from bot.utils.usage_events import record_usage_event

router = Router()
logger = logging.getLogger(__name__)
MAX_PROMPT_LEN = 1000
MAX_LYRICS_LEN = 5000


@router.callback_query(MusicTextAction.filter(F.action == "ai"))
async def lyrics_ai(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await update_music_data(
        state,
        prompt_source="ai",
        instrumental=False,
        custom_mode=True,
        prompt="",
        style="",
        title="",
        prompt_after_mode=False,
        prompt_after_title=False,
    )
    await edit_or_answer(
        query,
        text=MUSIC_PROMPT_AI_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.callback_query(MusicTextAction.filter(F.action == "manual"))
async def lyrics_manual(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await update_music_data(
        state,
        prompt_source="manual",
        instrumental=False,
        custom_mode=True,
        prompt="",
        style="",
        title="",
        prompt_after_mode=False,
        prompt_after_title=False,
    )
    await edit_or_answer(
        query,
        text=MUSIC_PROMPT_MANUAL_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.callback_query(MusicTextAction.filter(F.action == "instrumental"))
async def lyrics_instrumental(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await update_music_data(
        state,
        prompt_source="instrumental",
        instrumental=True,
        custom_mode=True,
        prompt="",
        style="",
        title="",
        prompt_after_mode=False,
        prompt_after_title=False,
    )
    await edit_or_answer(
        query,
        text=MUSIC_PROMPT_INSTRUMENTAL_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.message(MusicGenerationState.prompt)
async def prompt_received(
    message: Message,
    state: FSMContext,
    user: UserRD,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer("Текст не должен быть пустым.")
        return
    data = await get_music_data(state)
    if data.prompt_source == "manual" and len(prompt) > MAX_LYRICS_LEN:
        await message.answer("Текст песни слишком длинный. Укоротите до 5000 символов.")
        return
    if data.prompt_source != "manual" and len(prompt) > MAX_PROMPT_LEN:
        await message.answer("Промпт слишком длинный. Укоротите до 1000 символов.")
        return
    if data.prompt_source == "ai":
        if not await charge_user_credits(
            session=session,
            redis=redis,
            user=user,
            amount=1,
        ):
            await message.answer(
                "Недостаточно кредитов для генерации текста.",
                reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
            )
            return
        await message.answer("Генерирую текст песни...")
        try:
            lyrics = await _lyrics_client().generate_song_text(prompt=prompt)
        except AgentPlatformAPIError as err:
            logger.warning("Не удалось сгенерировать текст: %s", err)
            await refund_user_credits(
                session=session,
                redis=redis,
                user=user,
                amount=1,
            )
            await message.answer(
                "Не удалось сгенерировать текст песни. Попробуйте позже."
            )
            return

        await update_music_data(state, prompt=lyrics)
        preview = f"Текст песни:\n\n{lyrics}"
        await message.answer(preview[:4000])
        await record_usage_event(
            session=session,
            user_idpk=user.id,
            event_type=UsageEventType.AI_TEXT.value,
        )
    else:
        await update_music_data(state, prompt=prompt)
        if data.prompt_source == "manual":
            await record_usage_event(
                session=session,
                user_idpk=user.id,
                event_type=UsageEventType.MANUAL_TEXT.value,
            )

    if data.prompt_source == "instrumental":
        await ask_for_title(state, message, back_to=MusicBackTarget.PROMPT)
        return

    if data.prompt_source in {"ai", "manual", "instrumental"}:
        await ask_for_title(state, message, back_to=MusicBackTarget.PROMPT)
        return

    await state.clear()
    await message.answer(
        text=LYRICS_MENU_TEXT,
        reply_markup=await ik_music_text_menu(),
    )
