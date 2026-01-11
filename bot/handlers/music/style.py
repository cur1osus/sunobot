from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.redis.user_model import UserRD
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicStyle
from bot.keyboards.inline import ik_back_home
from bot.states import MusicGenerationState
from bot.utils.messaging import edit_or_answer
from bot.utils.music_helpers import start_generation
from bot.utils.music_state import update_music_data
from bot.utils.texts import MUSIC_STYLE_CUSTOM_TEXT

router = Router()


@router.message(MusicGenerationState.style)
async def style_received(
    message: Message,
    state: FSMContext,
    user: UserRD,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
) -> None:
    style = (message.text or "").strip()
    if not style:
        await message.answer("Стиль не должен быть пустым.")
        return

    await update_music_data(state, style=style)
    await start_generation_from_style(
        message,
        state,
        user=user,
        session=session,
        sessionmaker=sessionmaker,
        redis=redis,
    )


@router.callback_query(MusicStyle.filter(), MusicGenerationState.style)
async def style_selected(
    query: CallbackQuery,
    callback_data: MusicStyle,
    state: FSMContext,
    user: UserRD,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
) -> None:
    await query.answer()

    style_key = callback_data.style
    if style_key == "custom":
        await edit_or_answer(
            query,
            text=MUSIC_STYLE_CUSTOM_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TITLE),
        )
        return

    await update_music_data(state, style=style_key)
    await start_generation_from_style(
        query.message,
        state,
        user=user,
        session=session,
        sessionmaker=sessionmaker,
        redis=redis,
    )


async def start_generation_from_style(
    message: Message | None,
    state: FSMContext,
    *,
    user: UserRD,
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
) -> None:
    if message is None:
        return
    await start_generation(
        message,
        state,
        user=user,
        session=session,
        sessionmaker=sessionmaker,
        redis=redis,
    )
