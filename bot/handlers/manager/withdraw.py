from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.enum import TransactionStatus, TransactionType
from bot.db.models import TransactionModel, UserModel
from bot.keyboards.factories import WithdrawAction
from bot.settings import se

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(WithdrawAction.filter(F.action == "done"))
async def withdraw_done(
    query: CallbackQuery,
    callback_data: WithdrawAction,
    session: AsyncSession,
) -> None:
    manager_ids = se.withdraw.manager_ids
    if query.from_user.id not in manager_ids:
        await query.answer("Нет доступа к этой операции.", show_alert=True)
        return

    transaction = await session.scalar(
        select(TransactionModel).where(
            TransactionModel.id == callback_data.transaction_id
        )
    )
    if not transaction or transaction.type != TransactionType.WITHDRAW_REQUEST.value:
        await query.answer("Заявка не найдена.", show_alert=True)
        return

    if transaction.status == TransactionStatus.COMPLETED.value:
        await query.answer("Заявка уже завершена.", show_alert=True)
        return

    if transaction.manager_id and transaction.manager_id != query.from_user.id:
        await query.answer(
            "Заявка закреплена за другим менеджером.",
            show_alert=True,
        )
        return

    transaction.status = TransactionStatus.COMPLETED.value
    transaction.manager_id = query.from_user.id
    try:
        await session.commit()
    except Exception as err:
        await session.rollback()
        logger.warning("Не удалось завершить заявку на вывод: %s", err)
        await query.answer("Не удалось завершить заявку. Попробуйте позже.")
        return

    user_db = await session.scalar(
        select(UserModel).where(UserModel.id == transaction.user_idpk)
    )
    if user_db:
        try:
            await query.bot.send_message(
                user_db.user_id,
                "Ваша заявка на вывод средств обработана. Спасибо!",
            )
        except Exception as err:
            logger.warning("Не удалось уведомить пользователя о выводе: %s", err)

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception as err:
        logger.warning("Не удалось обновить сообщение менеджера: %s", err)

    await query.answer("Заявка отмечена как выполненная.")
