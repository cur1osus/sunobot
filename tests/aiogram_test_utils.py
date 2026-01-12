from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    AnswerPreCheckoutQuery,
    EditMessageReplyMarkup,
    EditMessageText,
    GetMe,
    GetMyName,
    RefundStarPayment,
    SendAudio,
    SendInvoice,
    SendMessage,
)
from aiogram.types import BotName, Chat, Message, User


@dataclass
class TestSession(BaseSession):
    calls: list[Any] = field(default_factory=list)
    _counter: int = 0

    def __post_init__(self) -> None:
        super().__init__()

    async def close(self) -> None:
        return None

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ):
        if False:
            yield b""
        return

    async def make_request(
        self,
        bot: Bot,
        method: Any,
        timeout: int | None = None,
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=bot.id, is_bot=True, first_name="Bot", username="TestBot")
        if isinstance(method, GetMyName):
            return BotName(name="TestBot")
        if isinstance(
            method,
            (
                SendMessage,
                EditMessageText,
                EditMessageReplyMarkup,
                SendInvoice,
                SendAudio,
            ),
        ):
            return self._make_message(method, bot)
        if isinstance(
            method,
            (AnswerCallbackQuery, AnswerPreCheckoutQuery, RefundStarPayment),
        ):
            return True
        return True

    def _make_message(self, method: Any, bot: Bot) -> Message:
        self._counter += 1
        chat_id = getattr(method, "chat_id", None) or 1
        text = getattr(method, "text", None) or "ok"
        return Message(
            message_id=self._counter,
            date=datetime.now(),
            chat=Chat(id=int(chat_id), type="private"),
            from_user=User(id=bot.id, is_bot=True, first_name="Bot"),
            text=text,
        )


class FakeBot(Bot):
    def __init__(self) -> None:
        super().__init__(token="123:TEST", session=TestSession())
