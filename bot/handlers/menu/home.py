from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.db.redis.user_model import UserRD
from bot.handlers.cmds.start import START_TEXT
from bot.keyboards.factories import MenuAction
from bot.keyboards.inline import ik_main
from bot.states import BaseUserState
from bot.utils.messaging import edit_text_if_possible

router = Router()


@router.callback_query(MenuAction.filter(F.action == "home"))
async def menu_home(
    query: CallbackQuery,
    state: FSMContext,
    user: UserRD,
) -> None:
    await query.answer()
    await state.set_state(BaseUserState.main)
    text = START_TEXT.format(user=user) if user else "Главное меню"
    if await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_main(),
    ):
        return
    await query.message.answer(text, reply_markup=await ik_main())
