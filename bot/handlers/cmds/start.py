from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart

from bot.db.redis.user_db_model import UserRD
from bot.keyboards.inline import ik_main

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession


router = Router()
logger = logging.getLogger(__name__)

START_TEXT = "🏠 Главное меню\n💰 Ваш баланс: {user.user_id} кредитов\n🎵 \
Что вы хотите сделать?"


@router.message(CommandStart(deep_link=True))
async def start_cmd_with_deep_link(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: UserRD,
) -> None:
    args = command.args.split() if command.args else []
    deep_link = args[0]
    if deep_link and user:
        await message.answer(f"Нашли deep link {deep_link}")


@router.message(CommandStart(deep_link=False))
async def start_cmd(
    message: Message,
    user: UserRD,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await message.answer(
        text=START_TEXT.format(user=user),
        reply_markup=await ik_main(),
    )
