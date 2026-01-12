from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import payments

pytestmark = pytest.mark.asyncio


async def test_pre_checkout_success(monkeypatch) -> None:
    monkeypatch.setattr(payments, "parse_payload", lambda _: ("stars", "1"))

    tariff = SimpleNamespace(price=10)
    monkeypatch.setattr(payments, "get_topup_method", lambda _: SimpleNamespace())
    monkeypatch.setattr(payments, "get_topup_tariff", lambda *_: tariff)

    pre_checkout = SimpleNamespace(
        invoice_payload="payload",
        total_amount=10,
        currency=payments.STARS_CURRENCY,
        answer=AsyncMock(),
    )

    await payments.pre_checkout(pre_checkout)

    pre_checkout.answer.assert_awaited_once_with(ok=True)


async def test_successful_payment_adds_credits(
    dummy_message,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    payment = SimpleNamespace(
        invoice_payload="payload",
        total_amount=10,
        currency=payments.STARS_CURRENCY,
        telegram_payment_charge_id="tg",
        provider_payment_charge_id="prov",
    )
    dummy_message.successful_payment = payment

    monkeypatch.setattr(payments, "parse_payload", lambda _: ("stars", "1"))
    monkeypatch.setattr(
        payments,
        "get_topup_tariff",
        lambda *_: SimpleNamespace(price=10, credits=5),
    )

    add_user_credits = AsyncMock()
    monkeypatch.setattr(payments, "add_user_credits", add_user_credits)
    apply_referral = AsyncMock()
    monkeypatch.setattr(payments, "_apply_referral_bonus", apply_referral)

    await payments.successful_payment(
        dummy_message, dummy_user, dummy_session, dummy_redis
    )

    add_user_credits.assert_awaited_once()
    apply_referral.assert_awaited_once()
    assert dummy_message.answers
