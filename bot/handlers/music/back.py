from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.db.redis.user_model import UserRD
from bot.handlers.cmds.start import START_TEXT
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicBack
from bot.keyboards.inline import (
    ik_back_home,
    ik_main,
    ik_music_modes,
    ik_music_styles,
    ik_music_text_menu,
)
from bot.states import BaseUserState, MusicGenerationState
from bot.utils.messaging import edit_text_if_possible
from bot.utils.music_helpers import LYRICS_MENU_TEXT, ask_for_title

router = Router()


@router.callback_query(MusicBack.filter())
async def music_back(
    query: CallbackQuery,
    callback_data: MusicBack,
    state: FSMContext,
    user: UserRD | None,
) -> None:
    await query.answer()
    target = MusicBackTarget(callback_data.target)

    if target == MusicBackTarget.HOME:
        await state.set_state(BaseUserState.main)
        text = START_TEXT.format(user=user) if user else "Главное меню"
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=await ik_main(),
        )
    elif target == MusicBackTarget.TEXT_MENU:
        await state.clear()
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=LYRICS_MENU_TEXT,
            reply_markup=await ik_music_text_menu(),
        )
    elif target == MusicBackTarget.MODE:
        await state.set_state(MusicGenerationState.choose_mode)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Выбери режим генерации Suno:",
            reply_markup=await ik_music_modes(),
        )
    elif target == MusicBackTarget.STYLE:
        await state.set_state(MusicGenerationState.style)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Выбери стиль или введи свой сообщением:",
            reply_markup=await ik_music_styles(),
        )
    elif target == MusicBackTarget.TITLE:
        await ask_for_title(state, query.message)
    elif target == MusicBackTarget.PROMPT:
        await state.set_state(MusicGenerationState.prompt)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Опиши промпт для генерации:",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
        )
