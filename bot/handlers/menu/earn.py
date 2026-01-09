from __future__ import annotations

from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.deep_linking import create_start_link
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from bot.db.models import UserModel
from bot.db.redis.user_model import UserRD
from bot.keyboards.factories import MenuAction
from bot.keyboards.inline import ik_earn_menu
from bot.utils.messaging import edit_text_if_possible

router = Router()


@router.callback_query(MenuAction.filter(F.action == "earn"))
async def menu_earn(
    query: CallbackQuery,
    user: UserRD,
    session: AsyncSession,
) -> None:
    await query.answer()
    bot_name = (await query.message.bot.get_my_name()).name
    ref_link = await create_start_link(
        bot=query.message.bot,
        payload=f"ref_{user.user_id}",
        encode=False,
    )
    share_text = (
        "Приглашайте друзей и получайте 20% от всех их платежей в течение года!"
    )
    referrals_count = await session.scalar(
        select(func.count(UserModel.user_id)).where(
            UserModel.referrer_id == user.user_id
        )
    )
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"
    text = (
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
        f"💰 Реферальный баланс: {_format_rub(user.balance)} руб.\n"
        # f"💳 Выплачено: {_format_rub(user.referral_paid)} руб.\n"
        # f"📈 Платежи рефералов: {user.referral_payments_count}\n"
        # f"🧾 Сумма на выдаче: {_format_rub(user.payout_amount)} руб.\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"{ref_link}\n\n"
        "📣 Приглашайте друзей и получайте 20% от всех их платежей "
        "в течение года!"
    )
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_earn_menu(share_url=share_url),
    )


def _format_rub(amount: int) -> str:
    safe_amount = max(amount, 0)
    return f"{safe_amount / 100:.2f}"
