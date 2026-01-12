from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.db.enum import TransactionStatus, TransactionType
from bot.handlers.cmds import create_deep_link, refund, start
from tests.fakes import DummyMessage, DummyState

pytestmark = pytest.mark.asyncio


async def test_start_cmd_with_deep_link_applies_referral(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    apply_referral = AsyncMock(return_value=True)
    send_main_menu = AsyncMock()
    monkeypatch.setattr(start, "apply_referral", apply_referral)
    monkeypatch.setattr(start, "send_main_menu", send_main_menu)

    command = SimpleNamespace(args="ref_123")
    await start.start_cmd_with_deep_link(
        dummy_message,
        command,
        dummy_session,
        dummy_user,
        dummy_redis,
        dummy_state,
    )

    assert dummy_state.state is None
    assert apply_referral.called
    assert len(dummy_message.answers) == 1
    send_main_menu.assert_awaited_once()


async def test_start_cmd_no_deep_link(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_user,
    monkeypatch,
) -> None:
    send_main_menu = AsyncMock()
    monkeypatch.setattr(start, "send_main_menu", send_main_menu)

    await start.start_cmd(dummy_message, dummy_user, dummy_state)

    assert dummy_state.state is None
    send_main_menu.assert_awaited_once()


async def test_refund_cmd_requires_admin(
    dummy_message: DummyMessage,
    dummy_user,
    dummy_session,
    dummy_redis,
) -> None:
    dummy_message.text = "/refund 123"
    await refund.refund_cmd(dummy_message, dummy_user, dummy_session, dummy_redis)

    assert dummy_message.answers


async def test_refund_cmd_success(
    dummy_message: DummyMessage,
    admin_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    dummy_message.text = "/refund 123"

    target_user = SimpleNamespace(id=10, user_id=123)
    transaction = SimpleNamespace(
        id=7,
        user_idpk=10,
        method="stars",
        type=TransactionType.TOPUP.value,
        status=TransactionStatus.SUCCESS.value,
        telegram_charge_id="charge",
        credits=6,
        details=None,
        created_at=None,
    )
    dummy_session.scalar.side_effect = [target_user, transaction]

    deduct_user_credits = AsyncMock()
    monkeypatch.setattr(refund, "deduct_user_credits", deduct_user_credits)

    await refund.refund_cmd(
        dummy_message,
        admin_user,
        dummy_session,
        dummy_redis,
    )

    assert transaction.status == TransactionStatus.REFUNDED.value
    deduct_user_credits.assert_awaited_once()
    assert dummy_message.answers


async def test_create_deep_link(dummy_message: DummyMessage, monkeypatch) -> None:
    create_link = AsyncMock(return_value="https://example.test")
    monkeypatch.setattr(create_deep_link, "create_start_link", create_link)

    await create_deep_link.add_new_bot(dummy_message)

    assert dummy_message.answers
