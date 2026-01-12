from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from aiogram import BaseMiddleware, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from bot.db.redis.user_model import UserRD
from bot.handlers import router as handlers_router
from bot.keyboards.factories import MenuAction
from tests.aiogram_test_utils import FakeBot

pytestmark = pytest.mark.asyncio


class InjectDataMiddleware(BaseMiddleware):
    def __init__(self, *, user, session, redis, sessionmaker) -> None:
        self._user = user
        self._session = session
        self._redis = redis
        self._sessionmaker = sessionmaker

    async def __call__(self, handler, event, data):  # type: ignore[override]
        data["user"] = self._user
        data["session"] = self._session
        data["redis"] = self._redis
        data["sessionmaker"] = self._sessionmaker
        return await handler(event, data)


def _make_message(bot: FakeBot, text: str) -> Message:
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        text=text,
    )
    return message.as_(bot)


def _make_callback(bot: FakeBot, data: str) -> CallbackQuery:
    message = _make_message(bot, "menu")
    callback = CallbackQuery(
        id="1",
        from_user=User(id=1, is_bot=False, first_name="Test"),
        chat_instance="1",
        data=data,
        message=message,
    )
    callback.as_(bot)
    message.as_(bot)
    return callback


@pytest.fixture(scope="module")
def test_bot() -> FakeBot:
    return FakeBot()


@pytest.fixture(scope="module")
def test_context():
    now = datetime.now()
    user = UserRD(
        id=100,
        user_id=100,
        name="Test",
        username="test",
        credits=10,
        role="user",
        referrer_id=None,
        balance=0,
        registration_datetime=now,
        last_active=now,
    )
    session = AsyncMock()
    redis = AsyncMock()
    sessionmaker = AsyncMock()
    return {"user": user, "session": session, "redis": redis, "sessionmaker": sessionmaker}


@pytest.fixture(scope="module")
def dispatcher(test_bot, test_context):
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(handlers_router)
    dp.update.outer_middleware(
        InjectDataMiddleware(
            user=test_context["user"],
            session=test_context["session"],
            redis=test_context["redis"],
            sessionmaker=test_context["sessionmaker"],
        )
    )
    return dp


async def test_dispatch_start_command(dispatcher: Dispatcher, test_bot: FakeBot) -> None:
    test_bot.session.calls.clear()
    message = _make_message(test_bot, "/start")
    update = Update(update_id=1, message=message)

    await dispatcher.feed_update(test_bot, update)

    assert any(call.__class__.__name__ == "SendMessage" for call in test_bot.session.calls)


async def test_dispatch_menu_home(dispatcher: Dispatcher, test_bot: FakeBot) -> None:
    test_bot.session.calls.clear()
    callback = _make_callback(test_bot, MenuAction(action="home").pack())
    update = Update(update_id=2, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)


async def test_dispatch_menu_how(dispatcher: Dispatcher, test_bot: FakeBot) -> None:
    test_bot.session.calls.clear()
    callback = _make_callback(test_bot, MenuAction(action="how").pack())
    update = Update(update_id=3, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)


async def test_dispatch_menu_topup(dispatcher: Dispatcher, test_bot: FakeBot) -> None:
    test_bot.session.calls.clear()
    callback = _make_callback(test_bot, MenuAction(action="topup").pack())
    update = Update(update_id=4, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)


async def test_dispatch_menu_earn(
    dispatcher: Dispatcher,
    test_bot: FakeBot,
    test_context,
) -> None:
    test_bot.session.calls.clear()
    test_context["session"].scalar.side_effect = [0, 0, 0, 0]
    callback = _make_callback(test_bot, MenuAction(action="earn").pack())
    update = Update(update_id=5, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)


async def test_dispatch_menu_info_admin(
    dispatcher: Dispatcher,
    test_bot: FakeBot,
    test_context,
    monkeypatch,
) -> None:
    test_bot.session.calls.clear()
    user = test_context["user"]
    old_role = user.role
    user.role = "admin"
    monkeypatch.setattr(
        "bot.handlers.menu.info.build_admin_info_text",
        AsyncMock(return_value="info"),
    )
    callback = _make_callback(test_bot, MenuAction(action="info").pack())
    update = Update(update_id=6, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    user.role = old_role
    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)


async def test_dispatch_menu_withdraw_low_balance(
    dispatcher: Dispatcher,
    test_bot: FakeBot,
    test_context,
) -> None:
    test_bot.session.calls.clear()
    user = test_context["user"]
    old_balance = user.balance
    user.balance = 0
    callback = _make_callback(test_bot, MenuAction(action="withdraw").pack())
    update = Update(update_id=7, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    user.balance = old_balance
    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)


async def test_dispatch_music_entry(dispatcher: Dispatcher, test_bot: FakeBot) -> None:
    test_bot.session.calls.clear()
    callback = _make_callback(test_bot, MenuAction(action="music").pack())
    update = Update(update_id=8, callback_query=callback)

    await dispatcher.feed_update(test_bot, update)

    assert any(call.__class__.__name__ == "EditMessageText" for call in test_bot.session.calls)
