from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.db.enum import UserRole
from bot.db.redis.user_model import UserRD
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicBack
from bot.keyboards.inline import (
    ik_back_home,
    ik_main,
    ik_music_styles,
    ik_music_text_menu,
)
from bot.states import BaseUserState, MusicGenerationState
from bot.utils.messaging import edit_or_answer
from bot.utils.music_state import get_music_data
from bot.utils.texts import (
    LYRICS_MENU_TEXT,
    MUSIC_PROMPT_AI_TEXT,
    MUSIC_PROMPT_INSTRUMENTAL_TEXT,
    MUSIC_PROMPT_MANUAL_TEXT,
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
            reply_markup=await ik_main(is_admin=user.role == UserRole.ADMIN.value),
        )
    elif target == MusicBackTarget.TEXT_MENU:
        await state.clear()
        await edit_or_answer(
            query,
            text=LYRICS_MENU_TEXT,
            reply_markup=await ik_music_text_menu(),
        )
    elif target == MusicBackTarget.MODE:
        data = await get_music_data(state)
        await state.set_state(MusicGenerationState.prompt)
        await edit_or_answer(
            query,
            text=_prompt_text(data.prompt_source),
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
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
            reply_markup=await ik_back_home(back_to=MusicBackTarget.PROMPT),
        )
    elif target == MusicBackTarget.PROMPT:
        data = await get_music_data(state)
        await state.set_state(MusicGenerationState.prompt)
        await edit_or_answer(
            query,
            text=_prompt_text(data.prompt_source),
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
        )


def _prompt_text(prompt_source: str | None) -> str:
    if prompt_source == "ai":
        return MUSIC_PROMPT_AI_TEXT
    if prompt_source == "manual":
        return MUSIC_PROMPT_MANUAL_TEXT
    if prompt_source == "instrumental":
        return MUSIC_PROMPT_INSTRUMENTAL_TEXT
    return MUSIC_PROMPT_TEXT
