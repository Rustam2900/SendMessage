import logging

from aiogram import Bot, Router, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from message.keyboards import get_main_menu
from message.models import BotAdmin, Channel, Post

from django.conf import settings
from aiogram.client.default import DefaultBotProperties

router = Router()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
CHANNEL_ID = -1002304690046
ADMIN_ID = 5189183957
logger = logging.getLogger(__name__)


def is_admin(user_id):
    return BotAdmin.objects.filter(user_id=user_id).exists()


@router.message(CommandStart())
async def welcome(message: Message):
    user_id = message.from_user.id

    user = await BotAdmin.objects.filter(telegram_id=user_id).afirst()

    if user:
        main_menu_markup = get_main_menu()
        await message.answer(
            text='salom dunyo',
            reply_markup=main_menu_markup,
            parse_mode="HTML"
        )
    else:

        await message.answer(text='salom', parse_mode="HTML")
