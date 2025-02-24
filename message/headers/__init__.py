from aiogram import Router

from bot.headers.handlers import router as handlers_router

from bot.headers.AdminBot import router as admin_router

router = Router()

router.include_router(handlers_router)
router.include_router(admin_router)
