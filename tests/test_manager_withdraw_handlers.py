from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot.db.enum import TransactionStatus, TransactionType
from bot.handlers.manager import withdraw
from bot.keyboards.reply import CANCEL_BUTTON_TEXT
from tests.fakes import DummyCallbackQuery, DummyMessage, DummyState

pytestmark = pytest.mark.asyncio


async def test_withdraw_done_marks_completed(
    dummy_query: DummyCallbackQuery,
    dummy_session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(withdraw.se.withdraw, "manager_ids", [1])
    transaction = SimpleNamespace(
        id=1,
        type=TransactionType.WITHDRAW_REQUEST.value,
        status=TransactionStatus.PENDING.value,
        manager_id=None,
        user_idpk=10,
    )
    user_db = SimpleNamespace(user_id=99)
    dummy_session.scalar.side_effect = [transaction, user_db]

    await withdraw.withdraw_done(
        dummy_query, SimpleNamespace(transaction_id=1), dummy_session
    )

    assert transaction.status == TransactionStatus.COMPLETED.value


async def test_withdraw_error_request_sets_state(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_session,
) -> None:
    dummy_query.from_user.id = 1
    withdraw.se.withdraw.manager_ids = [1]
    transaction = SimpleNamespace(
        id=2,
        type=TransactionType.WITHDRAW_REQUEST.value,
        status=TransactionStatus.PENDING.value,
        manager_id=None,
        user_idpk=10,
    )
    dummy_session.scalar.return_value = transaction

    await withdraw.withdraw_error_request(
        dummy_query,
        SimpleNamespace(transaction_id=2),
        dummy_state,
        dummy_session,
    )

    assert dummy_state.state is not None


async def test_withdraw_error_cancel_restores_keyboard(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_session,
) -> None:
    dummy_query.from_user.id = 1
    withdraw.se.withdraw.manager_ids = [1]
    transaction = SimpleNamespace(
        id=3,
        type=TransactionType.WITHDRAW_REQUEST.value,
        status=TransactionStatus.PENDING.value,
        manager_id=None,
    )
    dummy_session.scalar.return_value = transaction

    await withdraw.withdraw_error_cancel(
        dummy_query,
        SimpleNamespace(transaction_id=3),
        dummy_state,
        dummy_session,
    )

    assert dummy_state.state is None


async def test_withdraw_error_reason_marks_failed_and_refunds(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_session,
    dummy_redis,
) -> None:
    dummy_message.from_user = SimpleNamespace(id=1)
    withdraw.se.withdraw.manager_ids = [1]
    await dummy_state.update_data(transaction_id=4)
    dummy_message.text = "fail"

    transaction = SimpleNamespace(
        id=4,
        type=TransactionType.WITHDRAW_REQUEST.value,
        status=TransactionStatus.PENDING.value,
        manager_id=None,
        user_idpk=10,
        amount=10000,
        details=None,
    )
    user_db = SimpleNamespace(user_id=77, balance=0, id=10)
    dummy_session.scalar.side_effect = [transaction, user_db]

    await withdraw.withdraw_error_reason(
        dummy_message,
        dummy_state,
        dummy_session,
        dummy_redis,
    )

    assert transaction.status == TransactionStatus.FAILED.value
    assert user_db.balance == 10000
    assert dummy_message.answers


async def test_withdraw_error_reason_cancel(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_session,
    dummy_redis,
) -> None:
    dummy_message.from_user = SimpleNamespace(id=1)
    withdraw.se.withdraw.manager_ids = [1]
    await dummy_state.update_data(transaction_id=5)
    dummy_message.text = CANCEL_BUTTON_TEXT

    transaction = SimpleNamespace(
        id=5,
        type=TransactionType.WITHDRAW_REQUEST.value,
        status=TransactionStatus.PENDING.value,
        manager_id=None,
        user_idpk=10,
        amount=10000,
        details=None,
    )
    dummy_session.scalar.return_value = transaction

    await withdraw.withdraw_error_reason(
        dummy_message,
        dummy_state,
        dummy_session,
        dummy_redis,
    )

    assert dummy_state.state is None
