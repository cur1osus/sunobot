from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicStyle
from bot.keyboards.inline import ik_back_home
from bot.states import MusicGenerationState
from bot.utils.messaging import edit_text_if_possible
from bot.utils.music_helpers import ask_for_title

router = Router()


@router.message(MusicGenerationState.style)
async def style_received(message: Message, state: FSMContext) -> None:
    style = (message.text or "").strip()
    if not style:
        await message.answer("Стиль не должен быть пустым.")
        return

    await state.update_data(style=style)
    await ask_for_title(state, message)


@router.callback_query(MusicStyle.filter())
async def style_selected(
    query: CallbackQuery,
    callback_data: MusicStyle,
    state: FSMContext,
) -> None:
    await query.answer()
    if (await state.get_state()) != MusicGenerationState.style:
        return

    style_key = callback_data.style
    if style_key == "custom":
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Введи стиль сообщением (например, Jazz, Pop, Rock).",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
        )
        return

    await state.update_data(style=style_key)
    await ask_for_title(state, query.message)
