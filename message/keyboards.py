from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def get_main_menu():
    main_menu_keyboard = ReplyKeyboardMarkup(keyboard=[
        [
            KeyboardButton(text="admin ➕"),
            KeyboardButton(text="admin ➖")
        ],
        [
            KeyboardButton(text="kanal ➕"),
            KeyboardButton(text="kanal ➖")
        ]

    ], resize_keyboard=True)
    return main_menu_keyboard
