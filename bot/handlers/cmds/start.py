from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart

from bot.db.models import UserModel
from bot.db.redis.user_db_model import UserRD
from bot.keyboards.inline import ik_main
from bot.states import BaseUserState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession


router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart(deep_link=True))
async def start_cmd_with_deep_link(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: UserModel | None,
) -> None:
    args = command.args.split() if command.args else []
    deep_link = args[0]
    if deep_link and user:
        await message.answer(f"Нашли deep link {deep_link}")


@router.message(CommandStart(deep_link=False))
async def start_cmd(
    message: Message,
    user: UserRD | None,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(BaseUserState.main)
    await message.answer(f"Привет {user.name}!")
    menu_msg = await message.answer("Главное меню", reply_markup=await ik_main())
    await state.update_data(
        menu_msg_id=menu_msg.message_id,
        menu_chat_id=menu_msg.chat.id,
    )
