from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.inline import ik_music_styles
from bot.states import MusicGenerationState
from bot.utils.music_state import update_music_data
from bot.utils.texts import MUSIC_STYLE_TEXT

router = Router()


@router.message(MusicGenerationState.title)
async def title_received(
    message: Message,
    state: FSMContext,
) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым.")
        return

    await update_music_data(state, title=title, custom_mode=True)
    await state.set_state(MusicGenerationState.style)
    await message.answer(
        MUSIC_STYLE_TEXT,
        reply_markup=await ik_music_styles(),
    )
