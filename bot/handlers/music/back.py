from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.db.redis.user_model import UserRD
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
from bot.utils.messaging import edit_or_answer
from bot.utils.texts import (
    LYRICS_MENU_TEXT,
    MUSIC_MODES_TEXT,
    MUSIC_PROMPT_TEXT,
    MUSIC_STYLE_TEXT,
    MUSIC_TITLE_TEXT,
    main_menu_text,
)

router = Router()


@router.callback_query(MusicBack.filter())
async def music_back(
    query: CallbackQuery,
    callback_data: MusicBack,
    state: FSMContext,
    user: UserRD,
) -> None:
    await query.answer()
    target = MusicBackTarget(callback_data.target)

    if target == MusicBackTarget.HOME:
        await state.set_state(BaseUserState.main)
        await edit_or_answer(
            query,
            text=main_menu_text(user),
            reply_markup=await ik_main(),
        )
    elif target == MusicBackTarget.TEXT_MENU:
        await state.clear()
        await edit_or_answer(
            query,
            text=LYRICS_MENU_TEXT,
            reply_markup=await ik_music_text_menu(),
        )
    elif target == MusicBackTarget.MODE:
        await state.set_state(MusicGenerationState.choose_mode)
        await edit_or_answer(
            query,
            text=MUSIC_MODES_TEXT,
            reply_markup=await ik_music_modes(),
        )
    elif target == MusicBackTarget.STYLE:
        await state.set_state(MusicGenerationState.style)
        await edit_or_answer(
            query,
            text=MUSIC_STYLE_TEXT,
            reply_markup=await ik_music_styles(),
        )
    elif target == MusicBackTarget.TITLE:
        await state.set_state(MusicGenerationState.title)
        await edit_or_answer(
            query,
            text=MUSIC_TITLE_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
        )
    elif target == MusicBackTarget.PROMPT:
        await state.set_state(MusicGenerationState.prompt)
        await edit_or_answer(
            query,
            text=MUSIC_PROMPT_TEXT,
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
        )
