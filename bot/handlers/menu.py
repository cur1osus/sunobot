from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.db.redis.user_db_model import UserRD
from bot.handlers.cmds.start import START_TEXT
from bot.keyboards.factories import MenuAction
from bot.keyboards.inline import ik_back_home, ik_main
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


@router.callback_query(MenuAction.filter(F.action == "how"))
async def menu_how(query: CallbackQuery) -> None:
    await query.answer()
    text = (
        "Как это работает:\n"
        "1) Нажми «Создать новую песню» и выбери режим.\n"
        "2) Укажи стиль, название и промпт для трека.\n"
        "3) Мы отправим запрос в Suno и пришлём ссылки на готовую музыку."
    )
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_back_home(),
    )


@router.callback_query(MenuAction.filter(F.action == "topup"))
async def menu_topup(query: CallbackQuery) -> None:
    await query.answer()
    text = "Пополнение баланса скоро появится. Напишем, когда можно будет \
    оплатить кредиты."
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_back_home(),
    )


@router.callback_query(MenuAction.filter(F.action == "earn"))
async def menu_earn(query: CallbackQuery) -> None:
    await query.answer()
    bot_name = (await query.message.bot.get_my_name()).name
    text = f"Раздел «Заработать с {bot_name}» пока в разработке.\
    Следите за обновлениями."
    await edit_text_if_possible(
        query.message.bot,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=text,
        reply_markup=await ik_back_home(),
    )
