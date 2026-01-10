from __future__ import annotations

from dataclasses import dataclass

from aiogram.types import LabeledPrice

from bot.settings import se
from bot.utils.texts import TopupMethodInfo, TopupTariff

PAYLOAD_PREFIX = "topup"
STARS_CURRENCY = "XTR"
CARD_CURRENCY = "RUB"


@dataclass(frozen=True)
class InvoiceConfig:
    title: str
    description: str
    payload: str
    currency: str
    prices: list[LabeledPrice]
    provider_token: str


def build_payload(method: str, plan: int) -> str:
    return f"{PAYLOAD_PREFIX}:{method}:{plan}"


def parse_payload(payload: str) -> tuple[str, str] | None:
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != PAYLOAD_PREFIX:
        return None
    _, method, plan = parts
    return method, plan


def build_invoice(
    *,
    method: TopupMethodInfo,
    tariff: TopupTariff,
) -> InvoiceConfig:
    title = f"Пополнение: {tariff.credits} кредитов"
    description = f"{tariff.credits} кредитов ({tariff.songs} генераций песен)"
    payload = build_payload(method.key, tariff.plan)
    if method.key == "stars":
        currency = STARS_CURRENCY
        provider_token = ""
        amount = tariff.price
    else:
        currency = CARD_CURRENCY
        provider_token = se.payments.yookassa_provider_token
        amount = tariff.price * 100

    prices = [LabeledPrice(label=title, amount=amount)]
    return InvoiceConfig(
        title=title,
        description=description,
        payload=payload,
        currency=currency,
        prices=prices,
        provider_token=provider_token,
    )
