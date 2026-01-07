from enum import Enum


class MusicBackTarget(str, Enum):
    HOME = "home"
    MODE = "mode"
    TYPE = "type"
    STYLE = "style"
    TITLE = "title"
    PROMPT = "prompt"
