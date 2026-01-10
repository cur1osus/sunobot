from aiogram.filters.callback_data import CallbackData


class MenuAction(CallbackData, prefix="menu"):
    action: str


class MusicBack(CallbackData, prefix="music_back"):
    target: str


class MusicMode(CallbackData, prefix="music_mode"):
    mode: str


class MusicStyle(CallbackData, prefix="music_style"):
    style: str


class MusicTextAction(CallbackData, prefix="music_text"):
    action: str


class TopupMethod(CallbackData, prefix="topup_method"):
    method: str


class TopupPlan(CallbackData, prefix="topup_plan"):
    method: str
    plan: str


class WithdrawAction(CallbackData, prefix="withdraw"):
    action: str
    transaction_id: int
