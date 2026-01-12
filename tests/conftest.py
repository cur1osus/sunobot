from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bot.db.redis.user_model import UserRD
from tests.fakes import DummyBot, DummyCallbackQuery, DummyMessage, DummyState


@pytest.fixture
def dummy_bot() -> DummyBot:
    return DummyBot()


@pytest.fixture
def dummy_message(dummy_bot: DummyBot) -> DummyMessage:
    return DummyMessage(bot=dummy_bot)


@pytest.fixture
def dummy_query(dummy_bot: DummyBot, dummy_message: DummyMessage) -> DummyCallbackQuery:
    return DummyCallbackQuery(bot=dummy_bot, message=dummy_message)


@pytest.fixture
def dummy_state() -> DummyState:
    return DummyState()


@pytest.fixture
def user_factory():
    def _make(
        *,
        user_id: int = 100,
        role: str = "user",
        credits: int = 10,
        balance: int = 0,
        username: str | None = "test",
    ) -> UserRD:
        now = datetime.now()
        return UserRD(
            id=user_id,
            user_id=user_id,
            name="Test",
            username=username,
            credits=credits,
            role=role,
            referrer_id=None,
            balance=balance,
            registration_datetime=now,
            last_active=now,
        )

    return _make


@pytest.fixture
def dummy_user(user_factory):
    return user_factory()


@pytest.fixture
def admin_user(user_factory):
    return user_factory(role="admin")


@pytest.fixture
def dummy_session():
    session = AsyncMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def dummy_redis():
    redis = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def dummy_sessionmaker(dummy_session):
    async def _maker():
        return dummy_session

    return _maker


@pytest.fixture
def dummy_user_obj():
    return SimpleNamespace(id=1)
