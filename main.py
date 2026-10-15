import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, ALLOWED_USER_ID
from middlewares.auth import AuthMiddleware
from keyboards.inline import get_main_menu_keyboard, get_main_menu
from states.osint_states import OSINTStates
from modules.dorking import run_dorking
from modules import username, email_osint, dorking, metadata, network

# Asosiy router
base_router = Router()

@base_router.message(CommandStart())
@base_router.message(Command("menu"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "🕵️‍♂️ <b>Professional OSINT Botga xush kelibsiz!</b>\n\n"
        "Quyidagi bo‘limlardan birini tanlang:\n\n"
        "• <b>👤 Username qidirish:</b> 400+ ijtimoiy tarmoqlardan qidirish (Sherlock)\n"
        "• <b>✉️ Email tekshirish:</b> Pochta qaysi saytlarda mavjudligini aniqlash (Holehe)\n"
        "• <b>🔎 Ism bo'yicha Dorking:</b> Google/DuckDuckGo orqali ochiq ma’lumotlar\n"
        "• <b>🌐 Domen/IP tahlili:</b> DNS yozuvlari va WHOIS hisoboti\n"
        "• <b>📷 Rasm EXIF tahlili:</b> Kamera parametrlari va GPS geolokatsiya\n\n"
        "<i>Kerakli amalni tanlash uchun quyidagi tugmalardan birini bosing:</i>"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

@base_router.callback_query(F.data == "cancel_to_menu")
async def cancel_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔙 <b>Amal bekor qilindi.</b>\n\nAsosiy menyudan kerakli bo‘limni tanlang:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Dorking xabarini qabul qilish va natijani faylda jo'natish handleri
@base_router.message(OSINTStates.waiting_for_dork, F.text)
async def process_dork(message: Message, state: FSMContext):
    raw_text = message.text.strip()
    if raw_text.startswith("/"):
        return

    name = raw_text
    status = await message.answer(f"🔎 <b>{name}</b> bo‘yicha qidiruv ketmoqda...", parse_mode="HTML")

    # run_dorking endi matn va fayl yo'lini qaytaradi
    text, file_path = await run_dorking(name)
    await status.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)

    # Agar fayl mavjud bo'lsa, Telegram orqali yuboramiz
    if file_path and os.path.exists(file_path):
        doc = FSInputFile(file_path)
        await message.answer_document(doc, caption=f"📄 '{name}' bo‘yicha to‘liq hisobot")
        try:
            os.remove(file_path)  # Faylni yuborib bo'lgach o'chiramiz
        except OSError:
            pass

    await state.clear()
    await message.answer("Boshqa amaliyot tanlang:", reply_markup=get_main_menu())

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    logging.info(f"Bot ishga tushirilmoqda... Ruxsat berilgan Admin ID: {ALLOWED_USER_ID}")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Xavfsizlik: Faqat ruxsat berilgan adminga javob berish (AuthMiddleware)
    dp.message.outer_middleware(AuthMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())

    # Routerlarni ulash
    dp.include_router(base_router)
    dp.include_router(username.router)
    dp.include_router(email_osint.router)
    dp.include_router(dorking.router)
    dp.include_router(metadata.router)
    dp.include_router(network.router)

    # Eski kutilayotgan so'rovlarni tozalash va pollingni boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
