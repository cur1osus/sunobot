from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.enum import TransactionStatus, TransactionType, UserRole
from bot.db.func import deduct_user_credits
from bot.db.models import TransactionModel, UserModel
from bot.db.redis.user_model import UserRD

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("refund"))
async def refund_cmd(
    message: Message,
    user: UserRD,
    session: AsyncSession,
    redis: Redis,
) -> None:
    if user.role != UserRole.ADMIN.value:
        await message.answer("У вас нет прав на выполнение этой команды.")
        return

    parts = (message.text or "").strip().split()
    if len(parts) < 2:
        await message.answer(
            "Использование:\n"
            "/refund [user_id] - возврат последней транзакции пользователя\n"
            "/refund tx [transaction_id] - возврат по ID транзакции"
        )
        return

    # Возврат по ID транзакции: /refund tx <transaction_id>
    if parts[1].lower() == "tx":
        if len(parts) < 3 or not parts[2].isdigit():
            await message.answer("Использование: /refund tx [transaction_id]")
            return
        transaction, target_user = await _get_transaction_by_id(session, int(parts[2]))
        if not transaction:
            await message.answer("Транзакция не найдена.")
            return
        if not target_user:
            await message.answer("Пользователь транзакции не найден.")
            return
        target_user_id = target_user.user_id
    else:
        # Возврат по user_id: /refund <user_id>
        if not parts[1].isdigit():
            await message.answer("Использование: /refund [user_id]")
            return
        target_user_id = int(parts[1])
        target_user = await session.scalar(
            select(UserModel).where(UserModel.user_id == target_user_id)
        )
        if not target_user:
            await message.answer("Пользователь не найден.")
            return
        transaction = await _get_last_stars_transaction(session, target_user.id)
        if not transaction:
            await message.answer("Не найдена успешная транзакция в звездах.")
            return

    if not transaction.telegram_charge_id:
        logger.warning(
            "Нет telegram_charge_id для возврата: transaction_id=%s",
            transaction.id,
        )
        await message.answer("Не удалось вернуть платеж: отсутствует ID транзакции.")
        return

    try:
        refunded = await message.bot.refund_star_payment(
            user_id=target_user_id,
            telegram_payment_charge_id=transaction.telegram_charge_id,
        )
    except Exception as err:
        logger.warning("Ошибка при возврате звезд: %s", err)
        await message.answer("Не удалось вернуть платеж. Попробуйте позже.")
        return

    if not refunded:
        await message.answer("Возврат не выполнен. Попробуйте позже.")
        return

    transaction.status = TransactionStatus.REFUNDED.value
    transaction.details = (
        f"{transaction.details}. Возврат админом {user.user_id}"
        if transaction.details
        else f"Возврат админом {user.user_id}"
    )
    try:
        await session.commit()
    except Exception as err:
        await session.rollback()
        logger.warning("Не удалось сохранить статус возврата: %s", err)
        await message.answer(
            "Возврат выполнен, но не удалось сохранить статус. "
            "Проверьте транзакцию вручную."
        )
        return

    await deduct_user_credits(
        session=session,
        redis=redis,
        user_id=target_user_id,
        amount=transaction.credits,
    )

    await message.answer(
        f"Возврат выполнен.\n"
        f"ID транзакции: {transaction.id}\n"
        f"Пользователь: {target_user_id}\n"
        f"Списано Hit$: {transaction.credits}"
    )


async def _get_transaction_by_id(
    session: AsyncSession,
    transaction_id: int,
) -> tuple[TransactionModel | None, UserModel | None]:
    """Получить транзакцию по ID и связанного пользователя."""
    transaction = await session.scalar(
        select(TransactionModel).where(
            TransactionModel.id == transaction_id,
            TransactionModel.method == "stars",
            TransactionModel.type == TransactionType.TOPUP.value,
            TransactionModel.status == TransactionStatus.SUCCESS.value,
        )
    )
    if not transaction:
        return None, None

    target_user = await session.scalar(
        select(UserModel).where(UserModel.id == transaction.user_idpk)
    )
    return transaction, target_user


async def _get_last_stars_transaction(
    session: AsyncSession,
    user_idpk: int,
) -> TransactionModel | None:
    """Получить последнюю успешную транзакцию в звёздах для пользователя."""
    return await session.scalar(
        select(TransactionModel)
        .where(
            TransactionModel.user_idpk == user_idpk,
            TransactionModel.method == "stars",
            TransactionModel.type == TransactionType.TOPUP.value,
            TransactionModel.status == TransactionStatus.SUCCESS.value,
        )
        .order_by(TransactionModel.created_at.desc(), TransactionModel.id.desc())
    )
