from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


@dataclass
class DummyBot:
    name: str = "TestBot"
    sent_messages: list[dict[str, Any]] = field(default_factory=list)
    edited_messages: list[dict[str, Any]] = field(default_factory=list)
    reply_markup_edits: list[dict[str, Any]] = field(default_factory=list)
    refunds: list[dict[str, Any]] = field(default_factory=list)
    audio: list[dict[str, Any]] = field(default_factory=list)

    async def get_my_name(self) -> SimpleNamespace:
        return SimpleNamespace(name=self.name)

    async def edit_message_text(self, **kwargs: Any) -> None:
        self.edited_messages.append(kwargs)

    async def edit_message_reply_markup(self, **kwargs: Any) -> None:
        self.reply_markup_edits.append(kwargs)

    async def send_message(
        self, chat_id: int, text: str, reply_markup: Any = None
    ) -> None:
        self.sent_messages.append(
            {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        )

    async def send_audio(self, chat_id: int, audio: Any) -> None:
        self.audio.append({"chat_id": chat_id, "audio": audio})

    async def refund_star_payment(self, **kwargs: Any) -> bool:
        self.refunds.append(kwargs)
        return True


@dataclass
class DummyMessage:
    bot: DummyBot
    chat_id: int = 1
    message_id: int = 1
    text: str | None = None
    from_user: Any = None
    successful_payment: Any = None
    answers: list[dict[str, Any]] = field(default_factory=list)
    invoices: list[dict[str, Any]] = field(default_factory=list)
    reply_markup_edits: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.chat = SimpleNamespace(id=self.chat_id)

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:
        payload = {"text": text}
        payload.update(kwargs)
        self.answers.append(payload)

    async def answer_invoice(self, **kwargs: Any) -> None:
        self.invoices.append(kwargs)

    async def edit_reply_markup(self, reply_markup: Any = None) -> None:
        self.reply_markup_edits.append(reply_markup)


@dataclass
class DummyCallbackQuery:
    bot: DummyBot
    message: DummyMessage | None = None
    from_user: Any = None
    answers: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.from_user is None:
            self.from_user = SimpleNamespace(id=1)

    async def answer(
        self, text: str | None = None, show_alert: bool = False, **kwargs: Any
    ) -> None:
        payload = {"text": text, "show_alert": show_alert}
        payload.update(kwargs)
        self.answers.append(payload)


class DummyState:
    def __init__(self) -> None:
        self.state = None
        self.data: dict[str, Any] = {}

    async def set_state(self, state: Any) -> None:
        self.state = state

    async def get_state(self) -> Any:
        return self.state

    async def update_data(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if args:
            if len(args) != 1 or not isinstance(args[0], dict):
                raise TypeError("update_data expects a single dict arg")
            self.data.update(args[0])
        self.data.update(kwargs)
        return self.data

    async def get_data(self) -> dict[str, Any]:
        return dict(self.data)

    async def clear(self) -> None:
        self.state = None
        self.data = {}
