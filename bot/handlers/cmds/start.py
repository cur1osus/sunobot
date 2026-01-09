from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from sqlalchemy import select

from bot.db.models import UserModel
from bot.db.redis.user_model import UserRD
from bot.keyboards.inline import ik_main

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


router = Router()
logger = logging.getLogger(__name__)

START_TEXT = "🏠 Главное меню\n💰 Ваш баланс: {user.credits} кредитов\n🎵 \
Что вы хотите сделать?"


@router.message(CommandStart(deep_link=True))
async def start_cmd_with_deep_link(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: UserRD,
    redis: Redis,
) -> None:
    args = command.args.split() if command.args else []
    deep_link = args[0] if args else ""
    if deep_link and user:
        await _apply_referral(
            session=session,
            redis=redis,
            user=user,
            deep_link=deep_link,
        )
    await message.answer(
        text=START_TEXT.format(user=user),
        reply_markup=await ik_main(),
    )
    await message.answer("Ты воспользовался реферальной ссылкой!")


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


async def _apply_referral(
    *,
    session: AsyncSession,
    redis: Redis,
    user: UserRD,
    deep_link: str,
) -> None:
    if user.referrer_id:
        return
    referrer_id = _parse_inviter_id(deep_link)
    if referrer_id is None or referrer_id == user.user_id:
        return

    stmt = select(UserModel).where(UserModel.user_id == user.user_id)
    user_db = await session.scalar(stmt)
    if not user_db or user_db.referrer_id:
        return

    stmt = select(UserModel).where(UserModel.user_id == referrer_id)
    referrer_db = await session.scalar(stmt)
    if not referrer_db:
        return

    user_db.referrer_id = referrer_id
    await session.commit()

    await UserRD.delete(redis, user_db.user_id)


def _parse_inviter_id(payload: str) -> int | None:
    if not payload.startswith("ref_"):
        return None
    raw_id = payload.removeprefix("ref_").strip()
    if not raw_id.isdigit():
        return None
    return int(raw_id)
