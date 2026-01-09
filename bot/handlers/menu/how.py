from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.factories import MenuAction
from bot.keyboards.inline import ik_back_home
from bot.utils.messaging import edit_text_if_possible

router = Router()


@router.callback_query(MenuAction.filter(F.action == "how"))
async def menu_how(query: CallbackQuery) -> None:
    await query.answer()
    bot_info = await query.message.bot.get_me()
    text = f"""🎵 Как работает бот {bot_info.full_name}?

{bot_info.full_name} - самый простой способ создать свою песню даже если вы совсем не разбираетесь

1️⃣ Вы можете создать текст песни вручную или с помощью AI.
2️⃣ После этого бот сгенерирует вам песню на этот текст (1 генерация даёт 2 варианта песни).
3️⃣ Каждая генерация текста стоит 1 кредит.
4️⃣ Каждая генерация песни стоит 2 кредита.

💰 Если у вас закончились кредиты, вы можете пополнить баланс в меню."""
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_back_home(),
    )
