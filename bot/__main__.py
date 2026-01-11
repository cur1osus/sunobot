from __future__ import annotations

import asyncio
import logging
from asyncio import CancelledError
from datetime import datetime
from functools import partial
from zoneinfo import ZoneInfo

import msgspec
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import PRODUCTION
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot import handlers
from bot.db.base import close_db, create_db_session_pool, init_db
from bot.middlewares.throw_session import ThrowDBSessionMiddleware
from bot.middlewares.throw_user_model import ThrowUserMiddleware
from bot.scheduler import default_scheduler as scheduler
from bot.scheduler import logger as scheduler_logger
from bot.settings import Settings, se

load_dotenv()

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def _moscow_converter(timestamp: float) -> tuple:
    return datetime.fromtimestamp(timestamp, MOSCOW_TZ).timetuple()


class MoscowFormatter(logging.Formatter):
    converter = staticmethod(_moscow_converter)


def setup_logging() -> None:
    formatter = MoscowFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)


scheduler_logger.setLevel(logging.ERROR)
setup_logging()
logger = logging.getLogger(__name__)


async def start_scheduler(
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
    bot: Bot,
) -> None:
    while True:
        await scheduler.run_pending()
        await asyncio.sleep(1)


async def startup(dispatcher: Dispatcher, bot: Bot, se: Settings, redis: Redis) -> None:
    await bot.delete_webhook(drop_pending_updates=True)

    engine, db_session = await create_db_session_pool(se)
    await init_db(engine)

    dispatcher.workflow_data.update(
        {
            "sessionmaker": db_session,
            "db_session_closer": partial(close_db, engine),
            "redis": redis,
        }
    )

    dispatcher.update.outer_middleware(ThrowDBSessionMiddleware())
    dispatcher.update.outer_middleware(ThrowUserMiddleware())

    asyncio.create_task(
        start_scheduler(
            sessionmaker=db_session,
            redis=redis,
            bot=bot,
        )
    )

    logger.info("Бот запущен")


async def shutdown(dispatcher: Dispatcher) -> None:
    await dispatcher["db_session_closer"]()
    logger.info("Бот остановлен")


async def set_default_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="start"),
        ]
    )


async def main() -> None:
    if not se.suno.api_key:
        raise RuntimeError("SUNO_API_KEY не задан. Бот не может быть запущен.")

    api = PRODUCTION

    bot = Bot(
        token=se.bot_token,
        session=AiohttpSession(api=api),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    redis = await se.redis_dsn()
    storage = RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        json_loads=msgspec.json.decode,
        json_dumps=partial(lambda obj: str(msgspec.json.encode(obj), encoding="utf-8")),
    )

    dp = Dispatcher(
        storage=storage,
        events_isolation=SimpleEventIsolation(),
    )

    dp.include_routers(handlers.router)
    dp.startup.register(partial(startup, se=se, redis=redis))
    dp.shutdown.register(shutdown)
    await set_default_commands(bot)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        uvloop = __import__("uvloop")
        loop_factory = uvloop.new_event_loop

    except ModuleNotFoundError:
        loop_factory = asyncio.new_event_loop
        logger.info("uvloop не найден, используется стандартный цикл событий")

    try:
        with asyncio.Runner(loop_factory=loop_factory) as runner:
            runner.run(main())

    except (CancelledError, KeyboardInterrupt):
        __import__("sys").exit(0)
