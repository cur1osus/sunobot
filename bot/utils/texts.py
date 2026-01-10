from __future__ import annotations

from dataclasses import dataclass

from bot.db.redis.user_model import UserRD
from bot.utils.formatting import format_rub

MAIN_MENU_TEXT = (
    "🏠 Главное меню\n💰 Ваш баланс: {credits} кредитов\n🎵 Что вы хотите сделать?"
)

LYRICS_MENU_TEXT = (
    "Начнем с создания текста для песни.\n\n"
    "1. Вы можете сгенерировать текст песни по любому описанию "
    "(кнопка Сгенерировать текст с AI)\n\n"
    "2. Вы можете ввести текст вручную (кнопка Ввести текст вручную)\n\n"
    "Если нужен инструментал, выбери «Инструментал» — попросим промпт-описание."
)

MUSIC_MODES_TEXT = "Выбери режим генерации Suno:"
MUSIC_STYLE_TEXT = "Выбери стиль или введи свой сообщением:"
MUSIC_TITLE_TEXT = "Добавь название трека:"
MUSIC_PROMPT_TEXT = "Опиши промпт для генерации:"
MUSIC_PROMPT_INSTRUMENTAL_TEXT = "Опиши промпт для инструментала:"
MUSIC_PROMPT_AI_TEXT = "Опиши, какой текст песни нужно сгенерировать:"
MUSIC_PROMPT_MANUAL_TEXT = "Введи текст песни вручную:"
MUSIC_STYLE_CUSTOM_TEXT = "Введи стиль сообщением (например, Jazz, Pop, Rock)."

WITHDRAW_TEXT = "Вывод средств пока недоступен. Мы сообщим, когда он заработает."
TOPUP_METHODS_TEXT = "Выберите способ пополнения:"


@dataclass(frozen=True)
class TopupMethodInfo:
    key: str
    title_prefix: str
    currency_label: str
    button_prefix: str


@dataclass(frozen=True)
class TopupTariff:
    plan: str
    price: int
    credits: int
    songs: int


_TOPUP_METHODS = {
    "stars": TopupMethodInfo(
        key="stars",
        title_prefix="⭐️",
        currency_label="звёзд",
        button_prefix="⭐️",
    ),
    "card": TopupMethodInfo(
        key="card",
        title_prefix="💳",
        currency_label="руб",
        button_prefix="💳",
    ),
}

_TOPUP_TARIFFS: dict[str, list[TopupTariff]] = {
    "card": [
        TopupTariff(plan="199", price=199, credits=6, songs=3),
        TopupTariff(plan="490", price=490, credits=20, songs=10),
        TopupTariff(plan="990", price=990, credits=50, songs=25),
        TopupTariff(plan="1990", price=1990, credits=120, songs=60),
    ],
    "stars": [
        TopupTariff(plan="1", price=1, credits=6, songs=3),
        TopupTariff(plan="2", price=2, credits=20, songs=10),
        TopupTariff(plan="3", price=3, credits=50, songs=25),
        TopupTariff(plan="4", price=4, credits=120, songs=60),
    ],
}


def get_topup_method(method: str) -> TopupMethodInfo | None:
    return _TOPUP_METHODS.get(method)


def get_topup_tariffs(method: str) -> list[TopupTariff]:
    return list(_TOPUP_TARIFFS.get(method, []))


def get_topup_tariff(method: str, plan: str) -> TopupTariff | None:
    for tariff in _TOPUP_TARIFFS.get(method, []):
        if tariff.plan == plan:
            return tariff
    return None


def topup_tariffs_text(method: str) -> str:
    method_info = get_topup_method(method)
    if not method_info:
        return "Не удалось определить способ оплаты. Попробуйте снова."

    tariffs = get_topup_tariffs(method)
    if not tariffs:
        return "Тарифы временно недоступны. Попробуйте позже."

    tariffs_lines = "\n".join(
        f"🔹 {tariff.price} {method_info.currency_label} → "
        f"{tariff.credits} кредитов ({tariff.songs} генерации песен)"
        for tariff in tariffs
    )
    return (
        f"{method_info.title_prefix} Пополнение баланса\n\n"
        "Вы можете приобрести кредиты для генерации песен:\n\n"
        "✅ Стоимость генерации текста - 1 кредит\n"
        "✅ Стоимость генерации песни - 2 кредита (1 генерация песни "
        "создает сразу 2 варианта трека)\n\n"
        "💰 Тарифы:\n"
        f"{tariffs_lines}\n\n"
        "Выберите подходящий вариант:"
    )


def main_menu_text(user: UserRD) -> str:
    return MAIN_MENU_TEXT.format(credits=user.credits)


def how_text(bot_name: str) -> str:
    return (
        f"🎵 Как работает бот {bot_name}?\n\n"
        f"{bot_name} - самый простой способ создать свою песню даже если вы "
        "совсем не разбираетесь\n\n"
        "1️⃣ Вы можете создать текст песни вручную или с помощью AI.\n"
        "2️⃣ После этого бот сгенерирует вам песню на этот текст "
        "(1 генерация даёт 2 варианта песни).\n"
        "3️⃣ Каждая генерация текста стоит 1 кредит.\n"
        "4️⃣ Каждая генерация песни стоит 2 кредита.\n\n"
        "💰 Если у вас закончились кредиты, вы можете пополнить баланс в меню."
    )


def earn_text(
    *,
    bot_name: str,
    referrals_count: int,
    balance_kopeks: int,
    ref_link: str,
) -> str:
    return (
        f"💸 Зарабатывайте с {bot_name}!\n\n"
        "Получайте 20% от суммы оплат приглашенных пользователей "
        "в течение целого года!\n\n"
        "Как это работает?\n"
        "1️⃣ Вы публикуете реферальную ссылку на бота в соц сетях "
        "или отправляете друзьям\n"
        "2️⃣ Друзья пользуются ботом и оплачивают песни\n"
        "3️⃣ 20% от всех оплат зачисляется на ваш баланс\n"
        "4️⃣ Сумму от 1000 руб можно вывести на карту\n\n"
        f"👥 Ваши рефералы: {referrals_count}\n"
        f"💰 Реферальный баланс: {format_rub(balance_kopeks)} руб.\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"{ref_link}\n\n"
        "📣 Приглашайте друзей и получайте 20% от всех их платежей "
        "в течение года!"
    )
