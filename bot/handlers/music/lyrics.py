from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import MusicTextAction
from bot.keyboards.inline import ik_back_home, ik_music_modes
from bot.states import MusicGenerationState
from bot.utils.agent_platform import AgentPlatformAPIError
from bot.utils.messaging import edit_text_if_possible
from bot.utils.music_helpers import _lyrics_client, start_generation  # noqa: PLC2701

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(MusicTextAction.filter(F.action == "ai"))
async def lyrics_ai(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await state.update_data(prompt_source="ai", instrumental=False)
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Опиши, какой текст песни нужно сгенерировать:",
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.callback_query(MusicTextAction.filter(F.action == "manual"))
async def lyrics_manual(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await state.update_data(prompt_source="manual", instrumental=False)
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Введи текст песни вручную:",
        reply_markup=await ik_back_home(back_to=MusicBackTarget.TEXT_MENU),
    )


@router.callback_query(MusicTextAction.filter(F.action == "instrumental"))
async def lyrics_instrumental(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.choose_mode)
    await state.update_data(prompt_source="instrumental", instrumental=True)
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Выбери режим генерации Suno:",
        reply_markup=await ik_music_modes(),
    )


@router.message(MusicGenerationState.prompt)
async def prompt_received(message: Message, state: FSMContext) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer("Текст не должен быть пустым.")
        return

    data = await state.get_data()
    if data.get("prompt_source") == "ai":
        await message.answer("Генерирую текст песни...")
        try:
            lyrics = await _lyrics_client().generate_song_text(prompt=prompt)
        except AgentPlatformAPIError as err:
            logger.warning("Lyrics generation failed: %s", err)
            await message.answer(
                "Не удалось сгенерировать текст песни. Попробуйте позже."
            )
            return

        await state.update_data(prompt=lyrics)
        preview = f"Текст песни:\n\n{lyrics}"
        await message.answer(preview[:4000])
    else:
        await state.update_data(prompt=prompt)
    if data.get("prompt_after_mode") or data.get("prompt_after_title"):
        await state.update_data(prompt_after_mode=False, prompt_after_title=False)
        await start_generation(message, state)
        return

    await state.set_state(MusicGenerationState.choose_mode)
    await message.answer(
        text="Выбери режим генерации Suno:",
        reply_markup=await ik_music_modes(),
    )
