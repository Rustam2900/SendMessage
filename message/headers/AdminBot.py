import os
import logging

from aiogram import Router, F, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from django.conf import settings

from bot.db import get_user_statistics, get_all_users, get_user_language
from bot.keyboards import get_main_menu, get_admin_menu
from account.models import CustomUser
from bot.states import SendMessage

router = Router()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


# -------------------------------------->   Add Movie   <------------------------------------------- #


def get_admin_ids():
    admin_ids = os.getenv("ADMINS", "")
    print("#######################", admin_ids)
    return [int(admin_id.strip()) for admin_id in admin_ids.split(",") if admin_id.strip().isdigit()]


def is_admin(user_id):
    admin_ids = get_admin_ids()
    print("#################aliadmin", admin_ids)
    return user_id in admin_ids


@router.message(Command('admin'))
async def admin(message: Message):
    user_id = message.from_user.id
    print("################user_id", user_id)
    user_lang = await get_user_language(user_id)
    user = await CustomUser.objects.filter(telegram_id=user_id).afirst()
    main_menu_markup = get_main_menu(user_lang)
    admin_menu_markup = get_admin_menu()
    if is_admin(user_id):
        await message.answer(text="👮🏻‍♂️Admin Xushkelibsiz\n"
                                  "Iltimos, quyidagi buyruqlardan birini tanlang:", reply_markup=admin_menu_markup)
    else:
        await message.answer(text="👮🏻‍♂️Uzur siz Admin emassiz", reply_markup=main_menu_markup)


@router.message(F.text == "👤Statistika")
async def show_statistics(message: Message):
    user_id = message.from_user.id
    if is_admin(user_id):
        user_stats = await get_user_statistics()

        statistics = f"👤 Foydalanuvchilar:\n" \
                     f"24 soatda yangi foydalanuvchilar: {user_stats['new_users_24h']}\n" \
                     f"1 oyda yangi foydalanuvchilar: {user_stats['new_users_1_month']}\n" \
                     f"Jami foydalanuvchilar: {user_stats['total_users']}\n\n"

        try:
            await message.answer(text=statistics)
        except TelegramBadRequest as e:
            logging.error(f"Failed to send message to user {user_id}: {str(e)}")
            await message.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    else:
        await message.answer(
            text="Siz admin emassiz, statistikani ko'rish huquqiga ega emassiz.",
            reply_markup=None
        )


@router.message(F.text == "✍️ Habar yuborish")
async def send_message_users(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if is_admin(user_id):
        await state.set_state(SendMessage.msg)
        await message.answer(text='Reklama xabarini yuboring!', reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer('Sizga bu buyruqdan foydalana olmaysiz')


@router.message(SendMessage.msg)
async def send_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    users = await get_all_users()
    total_users = len(users)
    failed_count = 0
    failed_users = []

    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message.text if message.text else "Xabar yuborildi."
            )
        except Exception as e:
            failed_count += 1
            failed_users.append(user.telegram_id)
            print(f"Failed to send message to {user.telegram_id}: {e}")

    sent_count = total_users - failed_count
    await bot.send_message(
        chat_id=is_admin(user_id),
        text=(
            f"<b>Bot a'zolari soni:</b> {total_users}\n"
            f"<b>Yuborilmadi:</b> {failed_count}\n"
            f"<b>Yuborildi:</b> {sent_count}"
        ),
        parse_mode=ParseMode.HTML,
    )

    if failed_users:
        failed_list = "\n".join(str(u) for u in failed_users)
        await bot.send_message(
            chat_id=is_admin(user_id),
            text=f"<b>Ushbu foydalanuvchilarga xabar yuborilmadi:</b>\n{failed_list}",
            parse_mode=ParseMode.HTML,
        )
