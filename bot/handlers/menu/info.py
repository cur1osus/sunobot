from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.enum import UserRole
from bot.db.redis.user_model import UserRD
from bot.keyboards.factories import InfoPeriod, MenuAction
from bot.keyboards.inline import ik_info_periods
from bot.utils.admin_stats import build_admin_info_text
from bot.utils.messaging import edit_or_answer

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(MenuAction.filter(F.action == "info"))
async def menu_info(
    query: CallbackQuery,
    user: UserRD,
    session: AsyncSession,
) -> None:
    await query.answer()
    if user.role != UserRole.ADMIN.value:
        await query.answer("Нет доступа.", show_alert=True)
        return
    await _send_info(query, session, period="day")


@router.callback_query(InfoPeriod.filter())
async def menu_info_period(
    query: CallbackQuery,
    callback_data: InfoPeriod,
    user: UserRD,
    session: AsyncSession,
) -> None:
    await query.answer()
    if user.role != UserRole.ADMIN.value:
        await query.answer("Нет доступа.", show_alert=True)
        return
    await _send_info(query, session, period=callback_data.period)


async def _send_info(
    query: CallbackQuery,
    session: AsyncSession,
    *,
    period: str,
) -> None:
    try:
        text = await build_admin_info_text(session, period)
    except Exception as err:
        logger.warning("Не удалось собрать статистику: %s", err)
        await edit_or_answer(
            query,
            text="Не удалось собрать статистику. Попробуйте позже.",
            reply_markup=await ik_info_periods(period),
        )
        return

    await edit_or_answer(
        query,
        text=text,
        reply_markup=await ik_info_periods(period),
    )
