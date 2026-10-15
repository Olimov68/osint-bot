import os
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, LinkPreviewOptions
from aiogram.fsm.context import FSMContext

from states.osint_states import OSINTStates
from keyboards.inline import get_cancel_keyboard, get_main_menu_keyboard
from config import get_tool_path

router = Router()

@router.callback_query(F.data == "menu_username")
async def start_username_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OSINTStates.waiting_for_username)
    await callback.message.edit_text(
        "👤 <b>Username bo‘yicha qidirish</b>\n\n"
        "Qidirmoqchi bo‘lgan ijtimoiy tarmoq taxallusini (username) yuboring:\n"
        "<i>Masalan: <code>johndoe</code> yoki <code>elonmusk</code></i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(OSINTStates.waiting_for_username, F.text)
async def process_username_search(message: Message, state: FSMContext):
    raw_text = message.text.strip()
    if raw_text.startswith("/"):
        return

    username = raw_text.lstrip("@")

    # Xavfsizlik tekshiruvi: faqat ruxsat berilgan belgilar
    if not username or not username.replace("_", "").replace("-", "").replace(".", "").isalnum():
        await message.answer(
            "⚠️ <b>Noto‘g‘ri format!</b>\n"
            "Iltimos, faqat harflar, raqamlar, _, -, . belgilaridan iborat username kiriting.",
            reply_markup=get_cancel_keyboard()
        )
        return

    status_msg = await message.answer(
        f"🔍 <b>@{username}</b> bo‘yicha internet platformalarida qidiruv ketmoqda...\n"
        f"⏳ Bu jarayon 30-60 soniya vaqt olishi mumkin, kuting...",
    )

    result_file = f"{username}.txt"
    sherlock_cmd = get_tool_path("sherlock")

    try:
        # Xavfsiz subprocess: shell injection xavfi yo'q
        proc = await asyncio.create_subprocess_exec(
            sherlock_cmd,
            username,
            "--print-found",
            "--timeout", "5",
            "--output", result_file,
            "--txt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await proc.communicate()
        raw_output = stdout.decode("utf-8", errors="ignore")

        # Natijalarni saralash
        found_platforms = []
        for line in raw_output.splitlines():
            line_clean = line.strip()
            if "[+]" in line_clean:
                cleaned = line_clean.replace("[+]", "").strip()
                found_platforms.append(cleaned)

        if found_platforms:
            summary_text = (
                f"✅ <b>@{username}</b> bo‘yicha <b>{len(found_platforms)}</b> ta profil topildi:\n\n"
            )
            # Dastlabki 25 ta havolani matn sifatida ko'rsatish
            summary_text += "\n".join(f"• {item}" for item in found_platforms[:25])

            if len(found_platforms) > 25:
                summary_text += f"\n\n<i>...va yana {len(found_platforms) - 25} ta platforma hisobot faylida.</i>"

            # Telegram xabar limiti xavfsizligi
            if len(summary_text) > 4000:
                summary_text = summary_text[:3900] + "\n\n<i>...qolgan platformalar hisobot faylida.</i>"

            await status_msg.edit_text(
                summary_text,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

            # Agar fayl avtomatik yaratilmagan bo'lsa, uni qo'lda saqlaymiz
            if not os.path.exists(result_file):
                with open(result_file, "w", encoding="utf-8") as f:
                    f.write(f"@{username} bo'yicha hisobot ({len(found_platforms)} ta profil):\n\n")
                    for item in found_platforms:
                        f.write(f"{item}\n")

            # To'liq hisobot faylini (FSInputFile) Telegram orqali yuborish
            if os.path.exists(result_file):
                doc = FSInputFile(path=result_file, filename=f"sherlock_{username}.txt")
                await message.answer_document(doc, caption=f"📄 @{username} bo‘yicha to‘liq hisobot")

        else:
            await status_msg.edit_text(f"❌ <b>@{username}</b> bo‘yicha hech qanday ochiq profil topilmadi.")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Xatolik yuz berdi:\n<code>{str(e)}</code>")

    finally:
        # Ish tugagach, diskdagi vaqtinchalik hisobot faylini tozalash
        if os.path.exists(result_file):
            try:
                os.remove(result_file)
            except OSError:
                pass
        await state.clear()
        await message.answer("Bosh menyuga qaytish uchun tugmani bosing:", reply_markup=get_main_menu_keyboard())
