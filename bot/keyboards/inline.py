from typing import Final

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

LIMIT_BUTTONS: Final[int] = 100
BACK_BUTTON_TEXT = "🔙"


async def ik_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎵 Сгенерировать музыку", callback_data="menu:music")
    builder.adjust(1)
    return builder.as_markup()


async def ik_music_modes() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Быстрый (промпт)",
        callback_data="music:mode:quick",
    )
    builder.button(
        text="Кастом (стиль+название)",
        callback_data="music:mode:custom",
    )
    _append_nav(builder, back_to="home")
    builder.adjust(2)
    return builder.as_markup()


async def ik_music_types() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="С вокалом",
        callback_data="music:type:vocal",
    )
    builder.button(
        text="Инструментал",
        callback_data="music:type:instrumental",
    )
    _append_nav(builder, back_to="mode")
    builder.adjust(2)
    return builder.as_markup()


async def ik_back_home(
    back_to: str | None = "home", with_cancel: bool = True
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _append_nav(builder, back_to=back_to, include_cancel=with_cancel)
    builder.adjust(2 if back_to and with_cancel else 1)
    return builder.as_markup()


async def ik_music_styles() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎤 Pop", callback_data="music:style:Pop")
    builder.button(text="🎸 Rock", callback_data="music:style:Rock")
    builder.button(text="🎷 Jazz", callback_data="music:style:Jazz")
    builder.button(text="🎻 Classical", callback_data="music:style:Classical")
    builder.button(text="🎧 Electronic", callback_data="music:style:Electronic")
    builder.button(text="🎹 Lo-fi", callback_data="music:style:Lo-fi")
    builder.button(text="🎼 Ambient", callback_data="music:style:Ambient")
    builder.button(text="🎙 Hip-Hop", callback_data="music:style:Hip-Hop")
    builder.button(text="✏️ Свой стиль", callback_data="music:style:custom")
    _append_nav(builder, back_to="type", include_cancel=True)
    builder.adjust(2, 2, 2, 2, 1, 2)
    return builder.as_markup()


def _append_nav(
    builder: InlineKeyboardBuilder,
    *,
    back_to: str | None,
    include_cancel: bool = True,
) -> None:
    if back_to:
        builder.button(
            text="⬅️ Назад",
            callback_data=f"music:back:{back_to}",
        )
