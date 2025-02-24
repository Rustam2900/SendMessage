import asyncio
import logging
from aiogram import Bot, Dispatcher
from asgiref.sync import sync_to_async
from django.core.management import BaseCommand

from bot.headers import router
from bot.management.commands.commands import commands
from account.models import CustomUser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_logs.txt"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@sync_to_async
def get_all_user_ids():
    """Faqat telegram_id mavjud bo'lgan foydalanuvchilarni olish."""
    return list(CustomUser.objects.exclude(telegram_id=None).values_list("telegram_id", flat=True))


async def notify_users(bot: Bot, message: str):
    """Hamma foydalanuvchilarga xabar yuborish."""
    user_ids = await get_all_user_ids()
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Xabarni yuborishda xatolik yuz berdi: {e}")


async def startup(bot: Bot):
    await notify_users(bot, '<b>Bot ishga tushdi✅</b>')
    logging.info("Hamma foydalanuvchilarga bot ishga tushgani haqida xabar yuborildi.")


async def shutdown(bot: Bot):
    await notify_users(bot, '<b>Bot ishdan to\'xtadi🛑</b>')
    logging.info("Hamma foydalanuvchilarga bot ishdan to'xtagani haqida xabar yuborildi.")


async def main():
    print("Starting bot...")
    logging.basicConfig(level=logging.INFO)

    from bot.headers.handlers import bot
    dp = Dispatcher()
    await bot.set_my_commands(commands=commands)
    logger.info("Buyruqlar o'rnatildi.")
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)
    dp.include_router(router)
    logger.info("Router ulandi.")
    await dp.start_polling(bot)


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Bot ishga tushishda xatolik yuzz berdi {e}")
