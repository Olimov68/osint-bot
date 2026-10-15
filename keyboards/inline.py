from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Asosiy menyu uchun inline tugmalar
    """
    buttons = [
        [
            InlineKeyboardButton(text="👤 Username qidirish", callback_data="menu_username"),
            InlineKeyboardButton(text="✉️ Email tekshirish", callback_data="menu_email")
        ],
        [
            InlineKeyboardButton(text="🔎 Ism bo'yicha Dorking", callback_data="menu_dorking"),
            InlineKeyboardButton(text="🌐 Domen/IP tahlili", callback_data="menu_network")
        ],
        [
            InlineKeyboardButton(text="📷 Rasm EXIF tahlili", callback_data="menu_metadata")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Qulaylik uchun alias
get_main_menu = get_main_menu_keyboard

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Bekor qilish va asosiy menyuga qaytish tugmasi
    """
    buttons = [
        [
            InlineKeyboardButton(text="🔙 Bekor qilish / Asosiy menyu", callback_data="cancel_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
