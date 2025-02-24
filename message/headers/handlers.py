import logging

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async

from message.keyboards import get_main_menu
from message.models import BotAdmin, Channel, Post

from django.conf import settings
from aiogram.client.default import DefaultBotProperties

from message.states import AdminState, AdminStateChannel, PostState

router = Router()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = logging.getLogger(__name__)


def is_admin(user_id):
    return BotAdmin.objects.filter(user_id=user_id).exists()


@router.message(CommandStart())
async def welcome(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username

    user = await BotAdmin.objects.filter(telegram_id=user_id).afirst()

    if not user:
        await message.answer("❌ Siz admin emassiz!")
        return

    update_data = {}
    if not user.full_name and full_name:
        update_data["full_name"] = full_name
    if not user.tg_username and username:
        update_data["tg_username"] = username

    if update_data:
        await BotAdmin.objects.filter(telegram_id=user_id).aupdate(**update_data)

    main_menu_markup = get_main_menu()
    await message.answer(
        text="🔹 Salom, Admin! Asosiy menyudasiz.",
        reply_markup=main_menu_markup,
        parse_mode="HTML"
    )


@router.message(lambda message: message.text == "admin ➕")
async def ask_for_admin_id(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_admin_id)
    await message.answer("🆔 Yangi adminning Telegram ID sini yuboring:")


@router.message(AdminState.waiting_for_admin_id)
async def add_admin(message: Message, state: FSMContext):
    try:
        new_admin_id = int(message.text)
        existing_admin = await BotAdmin.objects.filter(telegram_id=new_admin_id).afirst()

        if existing_admin:
            await message.answer("❗ Bu foydalanuvchi allaqachon admin!")
        else:
            await BotAdmin.objects.acreate(telegram_id=new_admin_id)
            await message.answer(f"✅ Foydalanuvchi (ID: {new_admin_id}) admin sifatida qo‘shildi!")

        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam yuboring!")


@router.message(lambda message: message.text == "admin ➖")
async def show_admin_list(message: Message):
    admins = list(await sync_to_async(list)(BotAdmin.objects.all()))

    if not admins:
        await message.answer("❗ Hech qanday admin mavjud emas.")
        return

    keyboard = InlineKeyboardBuilder()

    for admin in admins:
        button_text = f"{admin.full_name or 'Noma‘lum'} ({admin.telegram_id})"
        keyboard.button(text=button_text, callback_data=f"del_admin:{admin.telegram_id}")

    keyboard.adjust(1)
    await message.answer("🛑 O‘chirmoqchi bo‘lgan adminni tanlang:", reply_markup=keyboard.as_markup())


@router.callback_query(lambda c: c.data.startswith("del_admin:"))
async def delete_admin(callback: CallbackQuery):
    admin_id = int(callback.data.split(":")[1])
    admin = await BotAdmin.objects.filter(telegram_id=admin_id).afirst()

    if admin:
        await admin.adelete()
        await callback.message.answer(f"❌ {admin.full_name or 'Admin'} (ID: {admin.telegram_id}) o‘chirildi!")
        await callback.answer("Admin o‘chirildi!", show_alert=True)
    else:
        await callback.answer("❗ Bu admin topilmadi.", show_alert=True)


@router.message(lambda message: message.text == "kanal ➕")
async def ask_for_admin_id(message: Message, state: FSMContext):
    await state.set_state(AdminStateChannel.channel_for_admin_id)
    await message.answer("🆔 Yangi kanal Telegram ID sini yuboring:")


@router.message(AdminStateChannel.channel_for_admin_id)
async def add_admin(message: Message, state: FSMContext):
    try:
        new_admin_id = int(message.text)
        existing_admin = await Channel.objects.filter(channel_id=new_admin_id).afirst()

        if existing_admin:
            await message.answer("❗ Bu kanal allaqachon admin!")
        else:
            await Channel.objects.acreate(channel_id=new_admin_id)
            await message.answer(f"✅ kanall (ID: {new_admin_id})  qo‘shildi!")

        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam yuboring!")


@router.message(lambda message: message.text == "kanal ➖")
async def show_admin_list(message: Message):
    admins = list(await sync_to_async(list)(Channel.objects.all()))

    if not admins:
        await message.answer("❗ Hech qanday kanall mavjud emas.")
        return

    keyboard = InlineKeyboardBuilder()

    for admin in admins:
        button_text = f"{admin.name or 'Noma‘lum'} ({admin.channel_id})"
        keyboard.button(text=button_text, callback_data=f"del_channel:{admin.channel_id}")

    keyboard.adjust(1)
    await message.answer("🛑 O‘chirmoqchi bo‘lgan kanall tanlang:", reply_markup=keyboard.as_markup())


@router.callback_query(lambda c: c.data.startswith("del_channel:"))
async def delete_admin(callback: CallbackQuery):
    admin_id = int(callback.data.split(":")[1])
    admin = await Channel.objects.filter(channel_id=admin_id).afirst()

    if admin:
        await admin.adelete()
        await callback.message.answer(f"❌ {admin.name or 'Kanall'} (ID: {admin.channel_id}) o‘chirildi!")
        await callback.answer("Kanall o‘chirildi!", show_alert=True)
    else:
        await callback.answer("❗ Bu Kanall topilmadi.", show_alert=True)


skip_button = KeyboardButton(text="O‘tkazib yuborish")
skip_keyboard = ReplyKeyboardMarkup(keyboard=[[skip_button]], resize_keyboard=True)


@router.message(lambda message: message.text == "Post ✉️")
async def start_post(message: Message, state: FSMContext):
    await state.set_state(PostState.title)
    await message.answer("Post sarlavhasini kiriting yoki o'tkazib yuboring:", reply_markup=skip_keyboard)


@router.message(PostState.title)
async def get_title(message: Message, state: FSMContext):
    if message.text != "O‘tkazib yuborish":
        await state.update_data(title=message.text)
    await state.set_state(PostState.message)
    await message.answer("Post matnini kiriting:")


@router.message(PostState.message)
async def get_message(message: Message, state: FSMContext):
    await state.update_data(message=message.text)
    await state.set_state(PostState.video_url)
    await message.answer("Video URL kiriting yoki o'tkazib yuboring:", reply_markup=skip_keyboard)


@router.message(PostState.video_url)
async def get_video_url(message: Message, state: FSMContext):
    if message.text != "O‘tkazib yuborish":
        await state.update_data(video_url=message.text)
    await state.set_state(PostState.image_url)
    await message.answer("Rasm URL kiriting yoki o'tkazib yuboring:", reply_markup=skip_keyboard)


@router.message(PostState.image_url)
async def get_image_url(message: Message, state: FSMContext):
    if message.text != "O‘tkazib yuborish":
        await state.update_data(image_url=message.text)

    data = await state.get_data()
    title = data.get("title", "Yo‘q")
    message_text = data.get("message", "Yo‘q")
    video_url = data.get("video_url", "Yo‘q")
    image_url = data.get("image_url", "Yo‘q")

    post_preview = f"📢 *Post preview:*\n\n"
    post_preview += f"📌 *Title:* {title}\n"
    post_preview += f"📝 *Message:* {message_text}\n"
    post_preview += f"🎥 *Video:* {video_url}\n"
    post_preview += f"🖼 *Image:* {image_url}\n\n"
    post_preview += "Kanallarga yuborishni xohlaysizmi?"

    confirm_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ha, yuborish"), KeyboardButton(text="Bekor qilish")]
        ], resize_keyboard=True
    )

    await state.set_state(PostState.confirm)
    await message.answer(post_preview, parse_mode="Markdown", reply_markup=confirm_keyboard)


@router.message(PostState.confirm)
async def confirm_post(message: Message, state: FSMContext):
    if message.text == "Ha, yuborish":
        data = await state.get_data()
        title = data.get("title", "")
        message_text = data.get("message", "")
        video_url = data.get("video_url", "")
        image_url = data.get("image_url", "")

        post = await sync_to_async(Post.objects.create)(
            title=title,
            message=message_text,
            video_url=video_url,
            image_url=image_url
        )

        active_channels = await sync_to_async(list)(Channel.objects.filter(active=True))

        for channel in active_channels:
            try:
                if video_url:
                    await bot.send_video(
                        chat_id=channel.channel_id,
                        video=video_url,
                        caption=message_text
                    )
                elif image_url:
                    await bot.send_photo(
                        chat_id=channel.channel_id,
                        photo=image_url,
                        caption=message_text
                    )
                else:
                    await bot.send_message(
                        chat_id=channel.channel_id,
                        text=message_text
                    )

                await sync_to_async(post.channels_sent.add)(channel)
                post.sent_count += 1
                await sync_to_async(post.save)()
            except Exception as e:
                print(f"Xatolik: {e}")

        main_menu_markup = get_main_menu()
        await message.answer("Post muvaffaqiyatli saqlandi va kanallarga yuborildi!", reply_markup=main_menu_markup)
        await state.clear()
