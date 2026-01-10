from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.redis.user_model import UserRD
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicMode
from bot.keyboards.inline import ik_back_home, ik_music_styles
from bot.states import MusicGenerationState
from bot.utils.messaging import edit_or_answer
from bot.utils.music_helpers import start_generation
from bot.utils.music_state import get_music_data, update_music_data
from bot.utils.texts import (
    MUSIC_PROMPT_INSTRUMENTAL_TEXT,
    MUSIC_PROMPT_TEXT,
    MUSIC_STYLE_TEXT,
)

router = Router()


@router.callback_query(MusicMode.filter(), MusicGenerationState.choose_mode)
async def music_mode_handler(
    query: CallbackQuery,
    callback_data: MusicMode,
    state: FSMContext,
    user: UserRD,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
) -> None:
    await query.answer()

    custom_mode = callback_data.mode == "custom"
    await update_music_data(state, custom_mode=custom_mode)
    data = await get_music_data(state)
    if data.instrumental:
        if custom_mode:
            await state.set_state(MusicGenerationState.style)
            await edit_or_answer(
                query,
                text=MUSIC_STYLE_TEXT,
                reply_markup=await ik_music_styles(),
            )
            return
        await state.set_state(MusicGenerationState.prompt)
        await update_music_data(
            state,
            prompt_source="instrumental",
            prompt_after_mode=True,
        )
        await edit_or_answer(
            query,
            text=MUSIC_PROMPT_INSTRUMENTAL_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.MODE),
        )
        return

    if not custom_mode:
        if data.prompt:
            await start_generation(
                query.message,
                state,
                user=user,
                session=session,
                sessionmaker=sessionmaker,
                redis=redis,
            )
            return
        await state.set_state(MusicGenerationState.prompt)
        await update_music_data(state, prompt_source="quick", prompt_after_mode=True)
        await edit_or_answer(
            query,
            text=MUSIC_PROMPT_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.MODE),
        )
        return

    await state.set_state(MusicGenerationState.style)
    await edit_or_answer(
        query,
        text=MUSIC_STYLE_TEXT,
        reply_markup=await ik_music_styles(),
    )
