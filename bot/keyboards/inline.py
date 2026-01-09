from typing import Final

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.enums import MusicBackTarget
from bot.keyboards.factories import (
    MenuAction,
    MusicBack,
    MusicMode,
    MusicStyle,
    MusicTextAction,
)

LIMIT_BUTTONS: Final[int] = 100
BACK_BUTTON_TEXT = "⬅️ Назад"


async def ik_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎼 Создать новую песню",
        callback_data=MenuAction(action="music").pack(),
    )
    builder.button(
        text="❓ Как это работает?",
        callback_data=MenuAction(action="how").pack(),
    )
    builder.button(
        text="💳 Пополнить баланс",
        callback_data=MenuAction(action="topup").pack(),
    )
    builder.button(
        text="🪙 Заработать",
        callback_data=MenuAction(action="earn").pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


async def ik_music_text_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🤖 Сгенерировать текст с AI",
        callback_data=MusicTextAction(action="ai").pack(),
    )
    builder.button(
        text="✍️ Ввести текст вручную",
        callback_data=MusicTextAction(action="manual").pack(),
    )
    builder.button(
        text="🎹 Инструментал",
        callback_data=MusicTextAction(action="instrumental").pack(),
    )
    builder.button(
        text=BACK_BUTTON_TEXT,
        callback_data=MenuAction(action="home").pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


async def ik_music_modes() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Быстрый (промпт)",
        callback_data=MusicMode(mode="quick").pack(),
    )
    builder.button(
        text="Кастом (стиль+название)",
        callback_data=MusicMode(mode="custom").pack(),
    )
    _append_nav(builder, back_to=MusicBackTarget.HOME)
    builder.adjust(1)
    return builder.as_markup()


async def ik_music_styles() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎤 Pop",
        callback_data=MusicStyle(style="Pop").pack(),
    )
    builder.button(
        text="🎸 Rock",
        callback_data=MusicStyle(style="Rock").pack(),
    )
    builder.button(
        text="🎷 Jazz",
        callback_data=MusicStyle(style="Jazz").pack(),
    )
    builder.button(
        text="🎻 Classical",
        callback_data=MusicStyle(style="Classical").pack(),
    )
    builder.button(
        text="🎧 Electronic",
        callback_data=MusicStyle(style="Electronic").pack(),
    )
    builder.button(
        text="🎹 Lo-fi",
        callback_data=MusicStyle(style="Lo-fi").pack(),
    )
    builder.button(
        text="🎼 Ambient",
        callback_data=MusicStyle(style="Ambient").pack(),
    )
    builder.button(
        text="🎙 Hip-Hop",
        callback_data=MusicStyle(style="Hip-Hop").pack(),
    )
    builder.button(
        text="✏️ Свой стиль",
        callback_data=MusicStyle(style="custom").pack(),
    )
    _append_nav(builder, back_to=MusicBackTarget.MODE)
    builder.adjust(2, 2, 2, 2, 1, 2)
    return builder.as_markup()


async def ik_back_home(
    back_to: MusicBackTarget | None = MusicBackTarget.HOME,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _append_nav(builder, back_to=back_to)
    builder.adjust(1)
    return builder.as_markup()


async def ik_earn_menu(share_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📤 Поделиться",
        url=share_url,
    )
    builder.button(
        text="🪙 Запросить вывод",
        callback_data=MenuAction(action="withdraw").pack(),
    )
    builder.button(
        text=BACK_BUTTON_TEXT,
        callback_data=MenuAction(action="home").pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


def _append_nav(
    builder: InlineKeyboardBuilder,
    *,
    back_to: MusicBackTarget | None,
) -> None:
    if back_to:
        builder.button(
            text=BACK_BUTTON_TEXT,
            callback_data=MusicBack(target=back_to.value).pack(),
        )
