from aiogram import Router

from . import cmds, manager, menu, music, payments

router = Router()
router.include_router(cmds.router)
router.include_router(menu.router)
router.include_router(music.router)
router.include_router(payments.router)
router.include_router(manager.router)
