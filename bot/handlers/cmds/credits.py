from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.db.enum import UserRole
from bot.db.redis.user_model import UserRD
from bot.utils.suno_api import SunoAPIError, build_suno_client

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("credits"))
async def credits_cmd(message: Message, user: UserRD) -> None:
    if user.role != UserRole.ADMIN.value:
        await message.answer("У вас нет прав на выполнение этой команды.")
        return

    client = build_suno_client()
    try:
        credits = await client.get_remaining_credits()
    except SunoAPIError as err:
        logger.warning("Не удалось получить кредиты: %s", err)
        await message.answer("Не удалось получить баланс кредитов. Попробуйте позже.")
        return

    await message.answer(f"У вас осталось {credits} (~{credits // 12} песен) кредитов.")
