from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.keyboards.inline import (
    ik_back_home,
    ik_main,
    ik_music_modes,
    ik_music_styles,
    ik_music_types,
)
from bot.settings import se
from bot.states import BaseUserState, MusicGenerationState
from bot.utils.messaging import edit_text_if_possible
from bot.utils.suno_api import SunoAPIError, build_suno_client

if TYPE_CHECKING:
    from bot.utils.suno_api import SunoClient


router = Router()


def _client_or_none() -> SunoClient | None:
    if not se.suno.api_key:
        return None
    return build_suno_client()


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BaseUserState.main)
    await _upsert_menu_message(
        state,
        text="Главное меню",
        reply_markup=await ik_main(),
        fallback=callback.message,
    )


@router.callback_query(F.data.startswith("music:back:"))
async def music_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    target = callback.data.split(":", 2)[-1]  # type: ignore[union-attr]
    data = await state.get_data()
    custom_mode = bool(data.get("custom_mode"))
    instrumental = bool(data.get("instrumental"))

    if target == "home":
        await state.set_state(BaseUserState.main)
        await _upsert_menu_message(
            state,
            text="Главное меню",
            reply_markup=await ik_main(),
            fallback=callback.message,
        )
    elif target == "mode":
        await state.set_state(MusicGenerationState.choose_mode)
        await _upsert_menu_message(
            state,
            text="Выбери режим генерации Suno:",
            reply_markup=await ik_music_modes(),
            fallback=callback.message,
        )
    elif target == "type":
        await state.set_state(MusicGenerationState.choose_type)
        await _upsert_menu_message(
            state,
            text="Выбери тип трека:",
            reply_markup=await ik_music_types(),
            fallback=callback.message,
        )
    elif target == "style":
        await state.set_state(MusicGenerationState.style)
        await _upsert_menu_message(
            state,
            text="Выбери стиль или введи свой сообщением:",
            reply_markup=await ik_music_styles(),
            fallback=callback.message,
        )
    elif target == "title":
        await _ask_for_title(state, callback.message)
    elif target == "prompt":
        await state.set_state(MusicGenerationState.prompt)
        back_to = "title" if custom_mode else "type"
        await _upsert_menu_message(
            state,
            text="Опиши трек (промпт):",
            reply_markup=await ik_back_home(back_to=back_to),
            fallback=callback.message,
        )


@router.callback_query(F.data == "menu:music")
@router.message(Command("music"))
async def music_entry(event: Message | CallbackQuery, state: FSMContext) -> None:
    message = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer()

    data_before = await state.get_data()
    menu_msg_id = data_before.get("menu_msg_id")
    menu_chat_id = data_before.get("menu_chat_id")

    await state.clear()
    if menu_msg_id and menu_chat_id:
        await state.update_data(menu_msg_id=menu_msg_id, menu_chat_id=menu_chat_id)

    client = _client_or_none()
    if not client:
        await _upsert_menu_message(
            state,
            text="SUNO_API_KEY не задан. Установите переменную окружения и перезапустите бота.",
            reply_markup=await ik_back_home(with_cancel=False),
            fallback=message,
        )
        return

    await state.set_state(MusicGenerationState.choose_mode)
    await _upsert_menu_message(
        state,
        text="Выбери режим генерации Suno:",
        reply_markup=await ik_music_modes(),
        fallback=message,
    )


@router.callback_query(F.data.startswith("music:mode:"))
async def music_mode_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if (await state.get_state()) != MusicGenerationState.choose_mode:
        return

    custom_mode = callback.data.endswith("custom")  # type: ignore[union-attr]
    await state.update_data(custom_mode=custom_mode)
    await state.set_state(MusicGenerationState.choose_type)
    await _upsert_menu_message(
        state,
        text="Выбери тип трека:",
        reply_markup=await ik_music_types(),
        fallback=callback.message,
    )


@router.callback_query(F.data.startswith("music:type:"))
async def music_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if (await state.get_state()) not in (
        MusicGenerationState.choose_type,
        MusicGenerationState.choose_mode,
    ):
        return

    custom_mode = bool((await state.get_data()).get("custom_mode"))
    instrumental = callback.data.endswith("instrumental")  # type: ignore[union-attr]
    await state.update_data(instrumental=instrumental, prompt=None)
    if custom_mode:
        await state.set_state(MusicGenerationState.style)
        await _upsert_menu_message(
            state,
            text="Выбери стиль или введи свой сообщением:",
            reply_markup=await ik_music_styles(),
            fallback=callback.message,
        )
    else:
        await state.set_state(MusicGenerationState.prompt)
        await _upsert_menu_message(
            state,
            text="Опиши трек (промпт):",
            reply_markup=await ik_back_home(back_to="type"),
            fallback=callback.message,
        )


@router.message(MusicGenerationState.prompt)
async def prompt_received(message: Message, state: FSMContext) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer("Промпт не должен быть пустым.")
        return

    await state.update_data(prompt=prompt)
    await start_generation(message, state)


@router.message(MusicGenerationState.style)
async def style_received(message: Message, state: FSMContext) -> None:
    style = (message.text or "").strip()
    if not style:
        await message.answer("Стиль не должен быть пустым.")
        return

    await state.update_data(style=style)
    await _ask_for_title(state, message)


@router.callback_query(F.data.startswith("music:style:"))
async def style_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if (await state.get_state()) != MusicGenerationState.style:
        return

    style_key = callback.data.split(":", 2)[-1]  # type: ignore[union-attr]
    if style_key == "custom":
        await _upsert_menu_message(
            state,
            text="Введи стиль сообщением (например, Jazz, Pop, Rock).",
            reply_markup=await ik_back_home(back_to="type"),
            fallback=callback.message,
        )
        return

    await state.update_data(style=style_key)
    await _ask_for_title(state, callback.message)


async def _ask_for_title(state: FSMContext, message: Message) -> None:
    await state.set_state(MusicGenerationState.title)
    await _upsert_menu_message(
        state,
        text="Добавь название трека:",
        reply_markup=await ik_back_home(back_to="style"),
        fallback=message,
    )


@router.message(MusicGenerationState.title)
async def title_received(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым.")
        return

    await state.update_data(title=title)
    await state.set_state(MusicGenerationState.prompt)
    await _upsert_menu_message(
        state,
        text="Опиши трек (промпт):",
        reply_markup=await ik_back_home(back_to="title"),
        fallback=message,
    )


async def start_generation(message: Message, state: FSMContext) -> None:
    client = _client_or_none()
    if not client:
        await _upsert_menu_message(
            state,
            text="SUNO_API_KEY не задан. Установите переменную окружения и перезапустите бота.",
            reply_markup=await ik_main(),
            fallback=message,
        )
        await state.clear()
        return

    data = await state.get_data()
    custom_mode = bool(data.get("custom_mode"))
    instrumental = bool(data.get("instrumental"))
    prompt = data.get("prompt", "")
    style = data.get("style", "") if custom_mode else ""
    title = data.get("title", "") if custom_mode else ""

    await state.set_state(MusicGenerationState.waiting)
    await _upsert_menu_message(
        state,
        text="Запускаю генерацию музыки в Suno...",
        reply_markup=None,
        fallback=message,
    )

    try:
        task_id = await client.generate_music(
            prompt=prompt,
            custom_mode=custom_mode,
            instrumental=instrumental,
            style=style,
            title=title,
        )
    except SunoAPIError as err:
        await _upsert_menu_message(
            state,
            text=f"Не удалось отправить запрос: {err}",
            reply_markup=await ik_main(),
            fallback=message,
        )
        await state.clear()
        return

    await _upsert_menu_message(
        state,
        text=f"Задача {task_id} создана. Ожидаю результат...",
        reply_markup=None,
        fallback=message,
    )

    try:
        status, details = await client.poll_task(task_id)
    except SunoAPIError as err:
        await _upsert_menu_message(
            state,
            text=f"Ошибка при получении статуса: {err}",
            reply_markup=await ik_main(),
            fallback=message,
        )
        await state.clear()
        return

    if status != "SUCCESS":
        await _upsert_menu_message(
            state,
            text=f"Задача завершилась со статусом: {status}",
            reply_markup=await ik_main(),
            fallback=message,
        )
        await state.clear()
        return

    response = details.get("response", {}) if isinstance(details, dict) else {}
    tracks = response.get("sunoData") or []
    if not tracks:
        await _upsert_menu_message(
            state,
            text="Готово, но ссылки на аудио не получены.",
            reply_markup=await ik_main(),
            fallback=message,
        )
        await state.clear()
        return

    await message.answer("Треки готовы:")
    for idx, track in enumerate(tracks, start=1):
        audio_url = track.get("audioUrl") or track.get("streamAudioUrl")
        title = track.get("title") or f"Трек {idx}"
        caption = "\n".join(
            filter(
                None,
                [
                    f"{title}",
                    f"Модель: {track.get('modelName')}",
                    f"Теги: {track.get('tags')}",
                    f"Промпт: {track.get('prompt')}",
                ],
            )
        )
        if audio_url:
            try:
                await message.answer_audio(
                    audio=audio_url,
                    caption=caption[:1024],
                )
            except Exception:
                await message.answer(f"{title}\nСсылка: {audio_url}")
        else:
            await message.answer(caption or f"{title} (без ссылки на аудио)")

    await _upsert_menu_message(
        state,
        text="Готово! Открой меню, чтобы запустить новую задачу.",
        reply_markup=await ik_main(),
        fallback=message,
    )
    await state.clear()


async def _upsert_menu_message(
    state: FSMContext,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    fallback: Message,
) -> None:
    data = await state.get_data()
    chat_id = data.get("menu_chat_id") or fallback.chat.id
    message_id = data.get("menu_msg_id")
    bot = fallback.bot

    if message_id and await edit_text_if_possible(
        bot,
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=reply_markup,
    ):
        return

    if await edit_text_if_possible(
        bot,
        chat_id=fallback.chat.id,
        message_id=fallback.message_id,
        text=text,
        reply_markup=reply_markup,
    ):
        await state.update_data(
            menu_msg_id=fallback.message_id,
            menu_chat_id=fallback.chat.id,
        )
        return

    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    await state.update_data(menu_msg_id=sent.message_id, menu_chat_id=chat_id)
