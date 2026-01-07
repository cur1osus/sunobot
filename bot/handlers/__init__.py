from aiogram import Router

from . import cmds, menu, music

router = Router()
router.include_router(cmds.router)
router.include_router(menu.router)
router.include_router(music.router)
