from aiogram import Router

from . import create_deep_link, credits, start

router = Router()
router.include_router(start.router)
router.include_router(create_deep_link.router)
router.include_router(credits.router)
