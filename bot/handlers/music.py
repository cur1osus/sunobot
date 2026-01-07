from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.db.redis.user_db_model import UserRD
from bot.handlers.cmds.start import START_TEXT
from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import (
    MenuAction,
    MusicBack,
    MusicMode,
    MusicStyle,
    MusicTextAction,
    MusicType,
)
from bot.keyboards.inline import (
    ik_back_home,
    ik_main,
    ik_music_modes,
    ik_music_styles,
    ik_music_text_menu,
    ik_music_types,
)
from bot.states import BaseUserState, MusicGenerationState
from bot.utils.messaging import edit_text_if_possible
from bot.utils.suno_api import SunoAPIError, build_suno_client

if TYPE_CHECKING:
    from bot.utils.suno_api import SunoClient


router = Router()

LYRICS_MENU_TEXT = (
    "Начнем с создания текста для песни.\n\n"
    "1. Вы можете сгенерировать текст песни по любому описанию "
    "(кнопка Сгенерировать текст с AI)\n\n"
    "2. Вы можете ввести текст вручную (кнопка Ввести текст вручную)"
)


def _client() -> SunoClient:
    return build_suno_client()


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
    elif target == MusicBackTarget.MODE:
        await state.set_state(MusicGenerationState.choose_mode)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Выбери режим генерации Suno:",
            reply_markup=await ik_music_modes(),
        )
    elif target == MusicBackTarget.TYPE:
        await state.set_state(MusicGenerationState.choose_type)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Выбери тип трека:",
            reply_markup=await ik_music_types(),
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
        await _ask_for_title(state, query.message)
    elif target == MusicBackTarget.PROMPT:
        await state.set_state(MusicGenerationState.prompt)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Опиши текст песни для генерации:",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.HOME),
        )


@router.callback_query(MenuAction.filter(F.action == "music"))
async def music_entry(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.clear()
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=LYRICS_MENU_TEXT,
        reply_markup=await ik_music_text_menu(),
    )


@router.callback_query(MusicTextAction.filter(F.action == "ai"))
async def lyrics_ai(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await state.update_data(prompt_source="ai")
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Опиши, какой текст песни нужно сгенерировать:",
        reply_markup=await ik_back_home(back_to=MusicBackTarget.HOME),
    )


@router.callback_query(MusicTextAction.filter(F.action == "manual"))
async def lyrics_manual(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(MusicGenerationState.prompt)
    await state.update_data(prompt_source="manual")
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Введи текст песни вручную:",
        reply_markup=await ik_back_home(back_to=MusicBackTarget.HOME),
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
            lyrics = await _client().generate_lyrics(prompt=prompt)
        except SunoAPIError as err:
            await message.answer(f"Не удалось сгенерировать текст: {err}")
            return

        await state.update_data(prompt=lyrics)
        preview = f"Текст песни:\n\n{lyrics}"
        await message.answer(preview[:4000])
    else:
        await state.update_data(prompt=prompt)
    await state.set_state(MusicGenerationState.choose_mode)
    await message.answer(
        text="Выбери режим генерации Suno:",
        reply_markup=await ik_music_modes(),
    )


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
    await state.set_state(MusicGenerationState.choose_type)
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Выбери тип трека:",
        reply_markup=await ik_music_types(),
    )


@router.callback_query(MusicType.filter())
async def music_type_handler(
    query: CallbackQuery,
    callback_data: MusicType,
    state: FSMContext,
) -> None:
    await query.answer()
    if (await state.get_state()) not in (
        MusicGenerationState.choose_type,
        MusicGenerationState.choose_mode,
    ):
        return

    data = await state.get_data()
    custom_mode = bool(data.get("custom_mode"))
    instrumental = callback_data.track_type == "instrumental"
    await state.update_data(instrumental=instrumental)

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

    if not data.get("prompt"):
        await state.set_state(MusicGenerationState.prompt)
        await edit_text_if_possible(
            query.message.bot,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="Опиши текст песни для генерации:",
            reply_markup=await ik_back_home(back_to=MusicBackTarget.HOME),
        )
        return

    await start_generation(query.message, state)


@router.message(MusicGenerationState.style)
async def style_received(message: Message, state: FSMContext) -> None:
    style = (message.text or "").strip()
    if not style:
        await message.answer("Стиль не должен быть пустым.")
        return

    await state.update_data(style=style)
    await _ask_for_title(state, message)


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
            reply_markup=await ik_back_home(back_to=MusicBackTarget.TYPE),
        )
        return

    await state.update_data(style=style_key)
    await _ask_for_title(state, query.message)


async def _ask_for_title(state: FSMContext, message: Message) -> None:
    await state.set_state(MusicGenerationState.title)
    await edit_text_if_possible(
        message.bot,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="Добавь название трека:",
        reply_markup=await ik_back_home(back_to=MusicBackTarget.STYLE),
    )


@router.message(MusicGenerationState.title)
async def title_received(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым.")
        return

    await state.update_data(title=title)
    await start_generation(message, state)


async def start_generation(message: Message, state: FSMContext) -> None:
    client = _client()
    data = await state.get_data()
    custom_mode = bool(data.get("custom_mode"))
    instrumental = bool(data.get("instrumental"))
    prompt = data.get("prompt", "")
    style = data.get("style", "") if custom_mode else ""
    title = data.get("title", "") if custom_mode else ""

    if not prompt:
        await message.answer("Текст песни не задан.")
        return

    await state.set_state(MusicGenerationState.waiting)
    await message.answer("Запускаю генерацию музыки в Suno...")

    try:
        task_id = await client.generate_music(
            prompt=prompt,
            custom_mode=custom_mode,
            instrumental=instrumental,
            style=style,
            title=title,
        )
    except SunoAPIError as err:
        await message.answer(f"Не удалось отправить запрос: {err}")
        await state.clear()
        return

    await message.answer(f"Задача {task_id} создана. Ожидаю результат...")

    try:
        status, details = await client.poll_task(task_id)
    except SunoAPIError as err:
        await message.answer(f"Ошибка при получении статуса: {err}")
        await state.clear()
        return

    if status != "SUCCESS":
        await message.answer(f"Задача завершилась со статусом: {status}")
        await state.clear()
        return

    response = details.get("response", {}) if isinstance(details, dict) else {}
    tracks = response.get("sunoData") or []
    if not tracks:
        await message.answer("Готово, но ссылки на аудио не получены.")
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

    await message.answer(
        "Готово! Открой меню, чтобы запустить новую задачу.",
        reply_markup=await ik_main(),
    )
    await state.clear()
