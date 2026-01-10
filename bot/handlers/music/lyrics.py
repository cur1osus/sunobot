from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.func import charge_user_credits, refund_user_credits
from bot.db.redis.user_model import UserRD
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicTextAction
from bot.keyboards.inline import ik_back_home, ik_music_modes
from bot.states import MusicGenerationState
from bot.utils.agent_platform import AgentPlatformAPIError
from bot.utils.messaging import edit_or_answer
from bot.utils.music_helpers import _lyrics_client, start_generation  # noqa: PLC2701
from bot.utils.music_state import get_music_data, update_music_data
from bot.utils.texts import (
    MUSIC_MODES_TEXT,
    MUSIC_PROMPT_AI_TEXT,
    MUSIC_PROMPT_MANUAL_TEXT,
)

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(MusicTextAction.filter(F.action == "ai"))
async def lyrics_ai(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await update_music_data(state, prompt_source="ai", instrumental=False)
    await edit_or_answer(
        query,
        text=MUSIC_PROMPT_AI_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.callback_query(MusicTextAction.filter(F.action == "manual"))
async def lyrics_manual(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await update_music_data(state, prompt_source="manual", instrumental=False)
    await edit_or_answer(
        query,
        text=MUSIC_PROMPT_MANUAL_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.callback_query(MusicTextAction.filter(F.action == "instrumental"))
async def lyrics_instrumental(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.choose_mode)
    await update_music_data(state, prompt_source="instrumental", instrumental=True)
    await edit_or_answer(
        query,
        text=MUSIC_MODES_TEXT,
        reply_markup=await ik_music_modes(),
    )


@router.message(MusicGenerationState.prompt)
async def prompt_received(
    message: Message,
    state: FSMContext,
    user: UserRD,
    session: AsyncSession,
    redis: Redis,
) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer("Текст не должен быть пустым.")
        return

    data = await get_music_data(state)
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
    else:
        await update_music_data(state, prompt=prompt)
    if data.prompt_after_mode or data.prompt_after_title:
        await update_music_data(
            state,
            prompt_after_mode=False,
            prompt_after_title=False,
        )
        await start_generation(
            message,
            state,
            user=user,
            session=session,
            redis=redis,
        )
        return

    await state.set_state(MusicGenerationState.choose_mode)
    await message.answer(
        text="Выбери режим генерации Suno:",
        reply_markup=await ik_music_modes(),
    )
