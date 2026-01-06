from aiogram.fsm.state import State, StatesGroup


class BaseUserState(StatesGroup):
    main = State()


class MusicGenerationState(StatesGroup):
    choose_mode = State()
    choose_type = State()
    prompt = State()
    style = State()
    title = State()
    waiting = State()
