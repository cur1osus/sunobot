from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.inline import ik_back_home
from bot.states import MusicGenerationState
from bot.utils.music_helpers import start_generation

router = Router()


@router.message(MusicGenerationState.title)
async def title_received(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым.")
        return

    await state.update_data(title=title)
    data = await state.get_data()
    if data.get("instrumental") and not data.get("prompt"):
        await state.set_state(MusicGenerationState.prompt)
        await state.update_data(prompt_source="instrumental", prompt_after_title=True)
        await message.answer(
            "Опиши промпт для инструментала:",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TITLE),
        )
        return
    await start_generation(message, state)
