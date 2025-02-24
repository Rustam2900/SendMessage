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

from account.models import CustomUser, VIPPackage, AddressMoney, OrderMinSum, VIPPackagePurchase
from bot.db import save_user_telegram_info, get_user_language, get_user_money_statistics
from bot.keyboards import get_languages, get_main_menu
from bot.states import UserStates, VIPPurchaseState, MoneyWithdrawal

from bot.utils import default_languages, introduction_template, user_languages
from django.conf import settings
from aiogram.client.default import DefaultBotProperties
from decimal import Decimal

router = Router()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
CHANNEL_ID = -1002304690046
ADMIN_ID = 5189183957
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def welcome(message: Message):
    user_id = message.from_user.id

    user = await CustomUser.objects.filter(telegram_id=user_id).afirst()

    if user and user.user_lang:
        main_menu_markup = get_main_menu(user.user_lang)
        await message.answer(
            text=introduction_template[user.user_lang],
            reply_markup=main_menu_markup,
            parse_mode="HTML"
        )
    else:
        msg = default_languages['welcome_message']
        await message.answer(text=msg, reply_markup=get_languages(), parse_mode="HTML")


@router.callback_query(lambda call: call.data.startswith("lang"))
async def get_query_languages(call: CallbackQuery, state: FSMContext):
    user_lang = call.data.split("_")[1]
    await state.update_data(user_lang=user_lang)

    await bot.answer_callback_query(call.id)
    await state.set_state(UserStates.ID)

    text = default_languages[user_lang]['ID']
    await call.message.answer(text, reply_markup=None)


@router.message(UserStates.ID)
async def reg_user_contact(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    user_lang = user_data.get("user_lang")

    input_id = message.text.strip()
    user = await CustomUser.objects.filter(generate_id=input_id).afirst()
    if user:
        if user.telegram_id:
            if user.telegram_id == user_id:
                full_name = user.full_name if user.full_name else message.from_user.username
                text = f"Hello or Привет, {full_name}!"
                await message.answer(text=text, reply_markup=get_main_menu(user_lang), parse_mode="HTML")
                await state.clear()
            else:
                error_text = default_languages[user_lang]['already_linked']
                await message.answer(text=error_text, reply_markup=None, parse_mode="HTML")
        else:
            await save_user_telegram_info(user, message, user_lang)
            full_name = user.full_name if user.full_name else message.from_user.username
            text = f"Hello or Привет, {full_name}!"
            await message.answer(text=text, reply_markup=get_main_menu(user_lang), parse_mode="HTML")
            await state.clear()
    else:
        error_text = default_languages[user_lang]['invalid_id']
        await message.answer(text=error_text, reply_markup=None, parse_mode="HTML")


@router.message(F.text.in_(["⚙️ Настройки", "⚙️ Settings"]))
async def settings(message: Message):
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    await message.answer(text=default_languages[user_lang]['select_language'], reply_markup=get_languages("setLang"))


def update_user_language(user_id, user_lang):
    try:
        user_language = CustomUser.objects.get(telegram_id=user_id)
        user_language.user_lang = user_lang
        user_language.save()
        print(f"User language updated for {user_id} to {user_lang}")
    except CustomUser.DoesNotExist:
        CustomUser.objects.create(telegram_id=user_id, user_lang=user_lang)
        print(f"User created with language {user_lang} for {user_id}")


@router.callback_query(F.data.startswith("setLang"))
async def change_language(call: CallbackQuery):
    user_id = call.from_user.id
    user_lang = call.data.split("_")[1]
    user_languages[call.from_user.id] = user_lang

    await sync_to_async(update_user_language)(user_id, user_lang)

    await call.message.answer(
        text=default_languages[user_lang]['successful_changed'],
        reply_markup=get_main_menu(user_lang)
    )


@router.message(F.text.in_(["Statistics", "Статистика"]))
async def show_statistics(message: Message):
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    user_stats = await get_user_money_statistics(user_id)

    statistics = (
        f"👤 <b>Statistika:</b>\n"
        f"💵 <b>{default_languages[user_lang]['user_balance_statistics']}:</b>\n"
        f"📅 {default_languages[user_lang]['earnings_24h']} <b>{user_stats['income_24h']} $</b>\n"
        f"📅 {default_languages[user_lang]['earnings_1_month']} <b>{user_stats['income_1_month']} $</b>\n"
        f"💰 {default_languages[user_lang]['total_earnings']} <b>{user_stats['total_income']} $</b>\n\n"

        # f"🏦 <b>VIP packages:</b>\n"
        # f"💎 {default_languages[user_lang]['total_spent_on_vip']}: <b>{user_stats['total_vip_spent']} $</b>\n"
    )

    try:
        await message.answer(text=statistics, parse_mode="HTML")
    except TelegramBadRequest as e:
        logging.error(f"Failed to send message to user {user_id}: {str(e)}")
        await message.answer("⚠️ Error.")


@router.message(F.text.in_(["deposit money", "вносить деньги"]))
async def show_vip_packages(message: Message):
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)

    vip_packages = await sync_to_async(list)(VIPPackage.objects.all())

    if not vip_packages:
        await message.answer(text=default_languages[user_lang]['not'])
        return

    inline_buttons = []
    for package in vip_packages:
        if user_lang == 'ru':
            button_text = f"{package.name_ru} - {package.price} $"
        else:
            button_text = f"{package.name_en} - {package.price} $"

        inline_buttons.append(
            [InlineKeyboardButton(text=button_text, callback_data=f"vip_{package.id}")]
        )
    inline_kb = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
    await message.answer(
        text=default_languages[user_lang]['vip_packege'],
        reply_markup=inline_kb
    )


@router.callback_query(F.data.startswith("vip_"))
async def show_vip_package_details(callback_query: CallbackQuery):
    package_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    user_lang = await get_user_language(user_id)

    try:
        package = await sync_to_async(VIPPackage.objects.get)(id=package_id)
    except VIPPackage.DoesNotExist:
        await callback_query.message.answer(text=default_languages[user_lang]['not'])
        return

    if user_lang == 'ru':
        caption_text = (
            f"<b>{package.name_ru}</b>\n\n"
            f"<b>{package.title_ru}</b>\n\n"
            f"{package.description_ru}\n\n"
            f"Цена: {package.price} $\n"
            f"Длительность: {package.duration} дней\n"
            f"Ежедневный доход: {package.daily_income_vip} $"
        )
        button_text = "Купить пакет"
    else:
        caption_text = (
            f"<b>{package.name_en}</b>\n\n"
            f"<b>{package.title_en}</b>\n\n"
            f"{package.description_en}\n\n"
            f"price: {package.price} $\n"
            f"Duration: {package.duration} day\n"
            f"Daily income: {package.daily_income_vip} $"
        )
        button_text = "Buy a package"

    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=button_text, callback_data=f"buy_{package.id}")]]
    )

    await callback_query.message.answer(
        text=caption_text,
        reply_markup=inline_kb
    )
    await callback_query.answer()


@router.callback_query(F.data.startswith("buy_"))
async def start_vip_purchase(callback_query: CallbackQuery, state: FSMContext):
    package_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    user_lang = await get_user_language(user_id)
    await state.update_data(package_id=package_id)
    try:
        address = await sync_to_async(AddressMoney.objects.first)()
    except AddressMoney.DoesNotExist:
        await callback_query.message.answer(
            text=default_languages[user_lang]['not']
        )
        return

    if not address or not address.telegram_address_money:
        await callback_query.message.answer(
            text=default_languages[user_lang]['not']
        )
        return

    await callback_query.message.answer(
        text=
        f"{default_languages[user_lang]['wallet_address']}\n"
        f"{address.telegram_address_money}\n\n"
        f"{default_languages[user_lang]['receipt_request']}",

        parse_mode="Markdown"
    )

    await state.set_state(VIPPurchaseState.waiting_for_receipt)


@router.message(VIPPurchaseState.waiting_for_receipt)
async def handle_receipt_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    data = await state.get_data()
    package_id = data.get('package_id')
    user = message.from_user
    await state.update_data(message_history=user_id)
    package = await sync_to_async(VIPPackage.objects.get)(id=package_id)
    try:
        web_user = await sync_to_async(CustomUser.objects.get)(telegram_id=user.id)
    except CustomUser.DoesNotExist:
        await message.answer(text=default_languages[user_lang]['not'])
        return
    if not message.photo:
        await message.answer(text=default_languages[user_lang]['user_check_photo_error'])
        return

    photo = message.photo[-1]

    inline_buttons = [
        [InlineKeyboardButton(text="Tasdiqlash", callback_data=f"confirm_{package.id}_{user.id}")],
        [InlineKeyboardButton(text="Bekor qilish", callback_data=f"cancel_{package.id}_{user.id}")]
    ]

    inline_kb = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
    caption = (
        f"🆔 <b>User Telegram ID:</b> {user.id}\n"
        f"🆔 <b>User Web ID:</b> {web_user.generate_id}\n"
        f"👤 <b>User:</b> {user.full_name or user.username}\n"
        f"📦 <b>Paket ID:</b> {package_id}\n"
        f"📦 <b>Paket Name:</b> {package.name}\n"
        f"📦 <b>Paket price:</b> {package.price}\n"
        f"✅ <b>Chek yuborildi, iltimos tekshiring.</b>"
    )

    admin_channel_id = -1002330025759
    try:
        await message.bot.send_photo(
            chat_id=admin_channel_id,
            photo=photo.file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=inline_kb
        )
    except Exception as e:
        await message.answer(text=default_languages[user_lang]['user_check_error'])
        print(f"Error sending photo to channel: {e}")
        return

    await message.answer(
        text=default_languages[user_lang]['user_check']
    )

    await state.clear()


# @router.callback_query(F.data.startswith("confirm_"))
# async def confirm_purchase(callback_query: CallbackQuery):
#     if callback_query.from_user.id != ADMIN_ID:
#         await callback_query.answer("❌ Sizda bu amalni bajarish huquqi yo'q!", show_alert=True)
#         return
#
#     data_parts = callback_query.data.split("_")
#     if len(data_parts) < 3:
#         await callback_query.answer("❌ Xatolik: Callback ma'lumotlari noto'g'ri!", show_alert=True)
#         return
#     package_id = int(data_parts[1])
#     user_id = int(data_parts[2])
#
#     user_lang = await get_user_language(user_id)
#
#     try:
#         package = await sync_to_async(VIPPackage.objects.get)(id=package_id)
#         user = await sync_to_async(CustomUser.objects.get)(telegram_id=user_id)
#     except (VIPPackage.DoesNotExist, CustomUser.DoesNotExist):
#         await callback_query.answer(text=default_languages[user_lang]['not'])
#         return
#
#     # VIP paket narxini foydalanuvchi hisobiga qo'shish
#     user.my_money += package.price
#     await sync_to_async(user.save)()
#
#     # Referalni olish va 10% qo'shish
#     referrer = await sync_to_async(user.team.first)()  # Refererni topish
#     if referrer:
#         referrer_bonus = package.price * 0.10  # 10% bonus
#         referrer.my_money += referrer_bonus
#         await sync_to_async(referrer.save)()  # Referer hisobi saqlanadi
#
#     # Xabarlarni yangilash va tasdiqlash
#     await callback_query.message.edit_reply_markup(reply_markup=None)
#     await callback_query.message.answer(
#         text=f"✅ {user.full_name or user.username} uchun {package.price}$ qo'shildi."
#     )
#     if referrer:
#         await callback_query.message.answer(
#             text=f"✅ Referal uchun {referrer_bonus}$ qo'shildi (taklif qilgan shaxs: {referrer.full_name or referrer.username})."
#         )
#     await callback_query.answer("✅ Muvaffaqiyatli tasdiqlandi!")
#     await callback_query.message.delete()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_purchase(callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("❌ Sizda bu amalni bajarish huquqi yo'q!", show_alert=True)
        return

    data_parts = callback_query.data.split("_")
    if len(data_parts) < 3:
        await callback_query.answer("❌ Xatolik: Callback ma'lumotlari noto'g'ri!", show_alert=True)
        return

    try:
        package_id = int(data_parts[1])
        user_id = int(data_parts[2])
    except ValueError:
        await callback_query.answer("❌ Xatolik: IDlar noto'g'ri formatda!", show_alert=True)
        return

    user_lang = await get_user_language(user_id)

    try:
        package = await sync_to_async(VIPPackage.objects.get)(id=package_id)
        user = await sync_to_async(CustomUser.objects.get)(telegram_id=user_id)
    except VIPPackage.DoesNotExist:
        await callback_query.answer(text=default_languages[user_lang]['package_not_found'], show_alert=True)
        return
    except CustomUser.DoesNotExist:
        await callback_query.answer(text=default_languages[user_lang]['user_not_found'], show_alert=True)
        return

    is_package_linked = await sync_to_async(lambda: user.vip_packages.filter(id=package.id).exists())()
    if not is_package_linked:
        await sync_to_async(user.vip_packages.add)(package)

    try:
        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=package.duration)

        purchase = VIPPackagePurchase(
            user=user,
            package=package,
            start_date=start_date,
            end_date=end_date,
        )
        await sync_to_async(purchase.save)()
    except Exception as e:
        print("Error during purchase save:", e)
        await callback_query.answer("❌ Xaridni saqlashda xatolik yuz berdi!", show_alert=True)
        return

    referrer = await sync_to_async(lambda: user.team.first())()
    if referrer:
        referrer_bonus = package.price * 0.10
        referrer.my_money += referrer_bonus
        await sync_to_async(referrer.save)()

    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(
        text=f"✅ {user.full_name or user.username} uchun {package.price}$ qo'shildi."
    )
    if referrer:
        await callback_query.message.answer(
            text=f"✅ Referal uchun {referrer_bonus}$ qo'shildi (taklif qilgan shaxs: {referrer.full_name or referrer.username})."
        )
    await callback_query.answer("✅ Muvaffaqiyatli tasdiqlandi!")
    await callback_query.message.delete()


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_purchase(callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("❌ Sizda bu amalni bajarish huquqi yo'q!", show_alert=True)
        return

    data_parts = callback_query.data.split("_")
    if len(data_parts) < 3:
        await callback_query.answer("❌ Xatolik: Callback ma'lumotlari noto'g'ri!", show_alert=True)
        return

    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(text="❌ To'lov bekor qilindi.")
    await callback_query.answer("❌ Bekor qilindi.")
    await callback_query.message.delete()


@router.message(F.text.in_(["issuing money", "выпуск денег"]))
async def issuing_money(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)

    user = await sync_to_async(CustomUser.objects.filter)(telegram_id=telegram_id)
    user = await sync_to_async(user.first)()

    if not user:
        await message.answer(default_languages[user_lang])
        return

    await state.set_state(MoneyWithdrawal.amount)
    await message.answer(default_languages[user_lang]['min_sum'])


async def send_to_channel(bot: Bot, user, amount):
    user_name = user.full_name if user.full_name else "not"
    tg_username = user.tg_username if user.tg_username else "not"
    wallet_address = user.address_money if user.address_money else "not"
    message = (
        f"💸 **Pul chiqarish so'rovi** 💸\n"
        f"👤 Foydalanuvchi: {user_name} (@{tg_username})\n"
        f"💵 Miqdor: {amount}$\n"
        f"🏦 Hamyon manzili: `{wallet_address}`"
    )
    # inline_buttons = [
    #     [InlineKeyboardButton(text="Tasdiqlash", callback_data=f"confirm_conf_{user.telegram_id}")],
    #     [InlineKeyboardButton(text="Bekor qilish", callback_data=f"cancel_can_{user.telegram_id}")]
    # ]
    # inline_kb = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
    await bot.send_message(CHANNEL_ID, message, parse_mode="HTML", reply_markup=None)


# @router.callback_query(F.data.startswith("confirm_conf_"))
# async def confirm_withdrawal(callback_query: CallbackQuery, bot: Bot):
#     user_id = int(callback_query.data.split("_")[1])
#     print("UserIDDDDDDDDDDDDDD", user_id)
#     if user_id != ADMIN_ID:
#         await bot.send_message(user_id, "❌ Sizda bu amalni bajarish huquqi yo'q!")
#         return
#     await bot.send_message(user_id, "✅ Sizning pulingiz hamyoningizga muvaffaqiyatli yuborildi.")
#     await callback_query.answer("✅ Pul chiqarish so'rovi tasdiqlandi.")
#     await callback_query.message.delete()
#
#
# @router.callback_query(F.data.startswith("cancel_can_"))
# async def cancel_withdrawal(callback_query: CallbackQuery, bot: Bot):
#     user_id = int(callback_query.data.split("_")[1])
#     print("UserIDDDDDDDDDDDDDD", user_id, "Cancel")
#
#     await bot.send_message(user_id, "❌ Uzr, sizning pulingiz keyinroq tashlab beriladi.")
#     await callback_query.answer("❌ Pul chiqarish so'rovi bekor qilindi.")
#     await callback_query.message.delete()


@router.message(MoneyWithdrawal.amount)
async def check_withdrawal_amount(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    amount_text = message.text.strip()

    try:
        amount = Decimal(amount_text)
    except ValueError:
        await message.answer(default_languages[user_lang]['min_sum_from'])
        return

    min_order_sum = await sync_to_async(OrderMinSum.objects.first)()
    user = await sync_to_async(CustomUser.objects.filter)(telegram_id=telegram_id)
    user = await sync_to_async(user.first)()

    if not min_order_sum or amount < min_order_sum.min_order_sum:
        await message.answer(f"Minimum summ: {min_order_sum.min_order_sum}")
        return

    if amount > user.my_money:
        await message.answer(default_languages[user_lang]['Insufficient_sum'])
        return

    try:
        await sync_to_async(handle_transaction)(telegram_id, amount)
    except Exception as e:
        logger.error(f"error: {e}")
        await message.answer(default_languages[user_lang]['Withdrawal_request'])
        return

    await state.update_data(amount=amount)

    if user.address_money:
        await message.answer(
            f"{default_languages[user_lang]['earnings_24h']} `{user.address_money}`",
            parse_mode="Markdown"
        )
        await send_to_channel(message.bot, user, amount)
        await state.clear()
    else:
        await state.set_state(MoneyWithdrawal.wallet)
        await message.answer(default_languages[user_lang]['please_address'])


def handle_transaction(telegram_id, amount):
    with transaction.atomic():
        user = CustomUser.objects.select_for_update().get(telegram_id=telegram_id)

        if amount > user.my_money:
            raise ValueError(default_languages[user.user_lang]['Insufficient_sum'])

        user.my_money -= amount
        user.save()
        logger.info(f"{user.telegram_id} foydalanuvchi hisobidan {amount}$ ayirildi.")


@router.message(MoneyWithdrawal.wallet)
async def save_wallet_address(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    wallet = message.text.strip()

    data = await state.get_data()
    amount = data.get("amount")

    user = await sync_to_async(CustomUser.objects.filter)(telegram_id=telegram_id)
    user = await sync_to_async(user.first)()

    user.address_money = wallet
    await sync_to_async(user.save)()

    await message.answer(
        f"{default_languages[user_lang]['earnings_24h']} `{wallet}`",
        parse_mode="Markdown"
    )

    await send_to_channel(message.bot, user, amount)
    await state.clear()
