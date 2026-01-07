from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.utils.suno_api import SunoAPIError, build_suno_client

router = Router()


@router.message(Command("credits"))
async def credits_cmd(message: Message) -> None:
    client = build_suno_client()
    try:
        credits = await client.get_remaining_credits()
    except SunoAPIError as err:
        await message.answer(f"Не удалось получить баланс кредитов: {err}")
        return

    await message.answer(f"У вас осталось {credits} (~{credits // 12} песен) кредитов.")
