from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.background_tasks import schedule_music_task
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.inline import ik_back_home, ik_main
from bot.states import MusicGenerationState
from bot.utils.agent_platform import build_agent_platform_client
from bot.utils.messaging import edit_text_if_possible
from bot.utils.suno_api import SunoAPIError, build_suno_client

if TYPE_CHECKING:
    from bot.utils.agent_platform import AgentPlatformClient
    from bot.utils.suno_api import SunoClient


logger = logging.getLogger(__name__)

MAX_QUICK_PROMPT_LEN = 500

LYRICS_MENU_TEXT = (
    "Начнем с создания текста для песни.\n\n"
    "1. Вы можете сгенерировать текст песни по любому описанию "
    "(кнопка Сгенерировать текст с AI)\n\n"
    "2. Вы можете ввести текст вручную (кнопка Ввести текст вручную)\n\n"
    "Если нужен инструментал, выбери «Инструментал» — попросим промпт-описание."
)


def _client() -> SunoClient:
    return build_suno_client()


def _lyrics_client() -> AgentPlatformClient:
    return build_agent_platform_client()


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


async def ask_for_title(state: FSMContext, message: Message) -> None:
    await state.set_state(MusicGenerationState.title)
    await edit_text_if_possible(
        message.bot,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="Добавь название трека:",
        reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
    )


async def start_generation(message: Message, state: FSMContext) -> None:
    client = _client()
    data = await state.get_data()
    custom_mode = bool(data.get("custom_mode"))
    instrumental = bool(data.get("instrumental"))
    prompt = data.get("prompt", "")
    generation_prompt = prompt
    style = data.get("style", "") if custom_mode else ""
    title = data.get("title", "") if custom_mode else ""

    if not generation_prompt:
        await message.answer("Промпт не задан.")
        return

    if not custom_mode and prompt and len(prompt) > MAX_QUICK_PROMPT_LEN:
        generation_prompt = prompt[:MAX_QUICK_PROMPT_LEN].rstrip()
        await state.update_data(prompt=generation_prompt)
        await message.answer(
            "Текст превышает 500 символов, обрезал для быстрого режима."
        )

    await state.set_state(MusicGenerationState.waiting)
    await message.answer("Запускаю генерацию музыки в Suno...")

    try:
        task_id = await client.generate_music(
            prompt=generation_prompt,
            custom_mode=custom_mode,
            instrumental=instrumental,
            style=style,
            title=title,
        )
    except SunoAPIError as err:
        logger.warning("Failed to start music generation: %s", err)
        await message.answer("Не удалось запустить генерацию музыки. Попробуйте позже.")
        await state.clear()
        return

    base_name = title.strip() if title.strip() else _first_line(prompt)
    if not base_name:
        base_name = "Трек"

    schedule_music_task(
        bot=message.bot,
        chat_id=message.chat.id,
        task_id=task_id,
        filename_base=base_name,
        poll_interval=client.poll_interval,
        poll_timeout=client.poll_timeout,
    )

    await message.answer(
        f"Задача {task_id} создана. Я пришлю файл, когда трек будет готов.",
        reply_markup=await ik_main(),
    )
    await state.clear()
