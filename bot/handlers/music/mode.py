from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicMode
from bot.keyboards.inline import ik_back_home, ik_music_styles
from bot.states import MusicGenerationState
from bot.utils.messaging import edit_text_if_possible
from bot.utils.music_helpers import start_generation

router = Router()


@router.callback_query(MusicMode.filter())
async def music_mode_handler(
    query: CallbackQuery,
    callback_data: MusicMode,
    state: FSMContext,
) -> None:
    await query.answer()
    if (await state.get_state()) != MusicGenerationState.choose_mode:
        return

    custom_mode = callback_data.mode == "custom"
    await state.update_data(custom_mode=custom_mode)
    data = await state.get_data()
    if data.get("instrumental"):
        if custom_mode:
            await state.set_state(MusicGenerationState.style)
            await edit_text_if_possible(
                query.message.bot,
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                text="Выбери стиль или введи свой сообщением:",
                reply_markup=await ik_music_styles(),
            )
            return
        await state.set_state(MusicGenerationState.prompt)
        await state.update_data(prompt_source="instrumental", prompt_after_mode=True)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Опиши промпт для инструментала:",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.MODE),
        )
        return

    if not custom_mode:
        if data.get("prompt"):
            await start_generation(query.message, state)
            return
        await state.set_state(MusicGenerationState.prompt)
        await state.update_data(prompt_source="quick", prompt_after_mode=True)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Опиши промпт для генерации:",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.MODE),
        )
        return

    await state.set_state(MusicGenerationState.style)
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Выбери стиль или введи свой сообщением:",
        reply_markup=await ik_music_styles(),
    )
