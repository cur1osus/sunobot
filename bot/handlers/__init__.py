from aiogram import Router

from . import cmds, music

router = Router()
router.include_router(cmds.router)
router.include_router(music.router)
