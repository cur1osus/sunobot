from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from aiogram.types import User
from sqlalchemy import select, update
from sqlalchemy.sql.operators import eq, ne

from .models import UserModel
from .redis.user_model import UserRD

if TYPE_CHECKING:
    from redis.asyncio.client import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _create_user(*, user: User, session: AsyncSession) -> UserModel:
    if user.username:
        stmt = select(UserModel).where(
            eq(UserModel.username, user.username), ne(UserModel.user_id, user.id)
        )
        another_user: UserModel | None = await session.scalar(stmt)

        if another_user:
            stmt = (
                update(UserModel)
                .where(eq(UserModel.user_id, another_user.user_id))
                .values(username=None)
            )
            await session.execute(stmt)

    stmt = select(UserModel).where(eq(UserModel.user_id, user.id))
    user_model: UserModel | None = await session.scalar(stmt)

    if not user_model:
        user_model = UserModel(
            user_id=user.id,
            username=user.username,
            name=user.first_name,
        )
        session.add(user_model)

    else:
        user_model.username = user.username
        user_model.name = user.first_name
        user_model.last_active = datetime.now(tz=UTC).replace(tzinfo=None)

    return cast(UserModel, user_model)


async def _get_user_model(
    *,
    db_pool: async_sessionmaker[AsyncSession],
    redis: Redis,
    user: User,
) -> UserRD:
    user_model: UserRD | None = await UserRD.get(redis, user.id)

    if user_model:
        return user_model

    async with db_pool() as session:
        async with session.begin():
            user_model: UserModel = await _create_user(
                user=user,
                session=session,
            )
            await session.commit()

        user_model: UserRD = UserRD.from_orm(cast(UserModel, user_model))

        await cast(UserRD, user_model).save(redis)

    return cast(UserRD, user_model)
