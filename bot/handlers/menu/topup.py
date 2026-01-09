from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.factories import MenuAction
from bot.keyboards.inline import ik_back_home
from bot.utils.messaging import edit_text_if_possible

router = Router()


@router.callback_query(MenuAction.filter(F.action == "topup"))
async def menu_topup(query: CallbackQuery) -> None:
    await query.answer()
    text = (
        "Пополнение баланса скоро появится. Напишем, когда можно будет "
        "оплатить кредиты."
    )
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_back_home(),
    )
