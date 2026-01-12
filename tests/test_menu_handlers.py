from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers.menu import earn, home, how, info, topup, withdraw
from bot.states import BaseUserState, WithdrawState
from tests.fakes import DummyCallbackQuery, DummyMessage, DummyState

pytestmark = pytest.mark.asyncio


async def test_menu_home_sets_state(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_user,
    monkeypatch,
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(home, "edit_or_answer", edit_or_answer)

    await home.menu_home(dummy_query, dummy_state, dummy_user)

    assert dummy_state.state == BaseUserState.main
    edit_or_answer.assert_awaited_once()


async def test_menu_how_shows_text(
    dummy_query: DummyCallbackQuery, monkeypatch
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(how, "edit_or_answer", edit_or_answer)

    await how.menu_how(dummy_query)

    edit_or_answer.assert_awaited_once()


async def test_menu_topup_shows_methods(
    dummy_query: DummyCallbackQuery, monkeypatch
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(topup, "edit_or_answer", edit_or_answer)

    await topup.menu_topup(dummy_query)

    edit_or_answer.assert_awaited_once()


async def test_topup_method_shows_plans(
    dummy_query: DummyCallbackQuery, monkeypatch
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(topup, "edit_or_answer", edit_or_answer)

    callback_data = SimpleNamespace(method="card")
    await topup.topup_method(dummy_query, callback_data)

    edit_or_answer.assert_awaited_once()


async def test_topup_plan_sends_invoice(
    dummy_message: DummyMessage, dummy_query: DummyCallbackQuery, monkeypatch
) -> None:
    dummy_query.message = dummy_message
    callback_data = SimpleNamespace(method="card", plan="199")

    invoice = SimpleNamespace(
        title="Title",
        description="Desc",
        payload="payload",
        provider_token="token",
        currency="RUB",
        prices=[SimpleNamespace(label="x", amount=100)],
    )
    monkeypatch.setattr(topup, "build_invoice", lambda **_: invoice)

    await topup.topup_plan(dummy_query, callback_data)

    assert dummy_message.invoices


async def test_menu_earn_builds_text(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    monkeypatch,
) -> None:
    create_link = AsyncMock(return_value="https://example.test")
    monkeypatch.setattr(earn, "create_start_link", create_link)
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(earn, "edit_or_answer", edit_or_answer)
    dummy_session.scalar.side_effect = [3, 2, 10000, 5000]

    await earn.menu_earn(dummy_query, dummy_state, dummy_user, dummy_session)

    edit_or_answer.assert_awaited_once()


async def test_menu_withdraw_low_balance(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    user_factory,
    monkeypatch,
) -> None:
    low_balance_user = user_factory(balance=100)
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(withdraw, "edit_or_answer", edit_or_answer)

    await withdraw.menu_withdraw(dummy_query, dummy_state, low_balance_user)

    assert dummy_state.state is None
    edit_or_answer.assert_awaited_once()


async def test_withdraw_amount_updates_state(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    user_factory,
) -> None:
    dummy_message.text = "1500"
    user = user_factory(balance=200000)

    await withdraw.withdraw_amount(dummy_message, dummy_state, user)

    assert dummy_state.state == WithdrawState.details


async def test_withdraw_details_creates_request(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    dummy_message.text = "details"
    await dummy_state.update_data(withdraw_amount=100000)

    withdraw_balance = AsyncMock(return_value=True)
    monkeypatch.setattr(withdraw, "withdraw_user_balance", withdraw_balance)
    monkeypatch.setattr(withdraw, "_select_manager_id", AsyncMock(return_value=None))

    await withdraw.withdraw_details(
        dummy_message,
        dummy_state,
        dummy_user,
        dummy_session,
        dummy_redis,
    )

    assert dummy_message.answers


async def test_menu_info_requires_admin(
    dummy_query: DummyCallbackQuery,
    dummy_user,
    dummy_session,
) -> None:
    await info.menu_info(dummy_query, dummy_user, dummy_session)

    assert dummy_query.answers


async def test_menu_info_admin(
    dummy_query: DummyCallbackQuery,
    admin_user,
    dummy_session,
    monkeypatch,
) -> None:
    build_admin_info_text = AsyncMock(return_value="info")
    monkeypatch.setattr(info, "build_admin_info_text", build_admin_info_text)
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(info, "edit_or_answer", edit_or_answer)

    await info.menu_info(dummy_query, admin_user, dummy_session)

    edit_or_answer.assert_awaited_once()


async def test_menu_info_period_admin(
    dummy_query: DummyCallbackQuery,
    admin_user,
    dummy_session,
    monkeypatch,
) -> None:
    build_admin_info_text = AsyncMock(return_value="info")
    monkeypatch.setattr(info, "build_admin_info_text", build_admin_info_text)
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(info, "edit_or_answer", edit_or_answer)

    callback_data = SimpleNamespace(period="day")
    await info.menu_info_period(dummy_query, callback_data, admin_user, dummy_session)

    edit_or_answer.assert_awaited_once()
