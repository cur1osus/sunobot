from aiogram.filters.callback_data import CallbackData


class MenuAction(CallbackData, prefix="menu"):
    action: str


class MusicBack(CallbackData, prefix="music_back"):
    target: str


class MusicMode(CallbackData, prefix="music_mode"):
    mode: str


class MusicType(CallbackData, prefix="music_type"):
    track_type: str


class MusicStyle(CallbackData, prefix="music_style"):
    style: str


class MusicTextAction(CallbackData, prefix="music_text"):
    action: str
