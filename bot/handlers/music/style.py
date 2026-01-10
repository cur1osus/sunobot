from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicStyle
from bot.keyboards.inline import ik_back_home
from bot.states import MusicGenerationState
from bot.utils.messaging import edit_or_answer
from bot.utils.music_helpers import ask_for_title
from bot.utils.music_state import update_music_data
from bot.utils.texts import MUSIC_STYLE_CUSTOM_TEXT, MUSIC_TITLE_TEXT

router = Router()


@router.message(MusicGenerationState.style)
async def style_received(message: Message, state: FSMContext) -> None:
    style = (message.text or "").strip()
    if not style:
        await message.answer("Стиль не должен быть пустым.")
        return

    await update_music_data(state, style=style)
    await ask_for_title(state, message)


@router.callback_query(MusicStyle.filter(), MusicGenerationState.style)
async def style_selected(
    query: CallbackQuery,
    callback_data: MusicStyle,
    state: FSMContext,
) -> None:
    await query.answer()

    style_key = callback_data.style
    if style_key == "custom":
        await edit_or_answer(
            query,
            text=MUSIC_STYLE_CUSTOM_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
        )
        return

    await update_music_data(state, style=style_key)
    await state.set_state(MusicGenerationState.title)
    await edit_or_answer(
        query,
        text=MUSIC_TITLE_TEXT,
        reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
    )
