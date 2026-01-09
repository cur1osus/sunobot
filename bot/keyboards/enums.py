from enum import Enum


class MusicBackTarget(str, Enum):
    HOME = "home"
    TEXT_MENU = "text_menu"
    MODE = "mode"
    STYLE = "style"
    TITLE = "title"
    PROMPT = "prompt"
