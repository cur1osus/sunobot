from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.redis.user_model import UserRD
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.inline import ik_back_home
from bot.states import MusicGenerationState
from bot.utils.music_helpers import start_generation
from bot.utils.music_state import get_music_data, update_music_data
from bot.utils.texts import MUSIC_PROMPT_INSTRUMENTAL_TEXT

router = Router()


@router.message(MusicGenerationState.title)
async def title_received(
    message: Message,
    state: FSMContext,
    user: UserRD,
    session: AsyncSession,
    redis: Redis,
) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым.")
        return

    await update_music_data(state, title=title)
    data = await get_music_data(state)
    if data.instrumental and not data.prompt:
        await state.set_state(MusicGenerationState.prompt)
        await update_music_data(
            state,
            prompt_source="instrumental",
            prompt_after_title=True,
        )
        await message.answer(
            MUSIC_PROMPT_INSTRUMENTAL_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TITLE),
        )
        return
    await start_generation(
        message,
        state,
        user=user,
        session=session,
        redis=redis,
    )
