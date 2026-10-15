import os
import re
import csv
import glob
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from states.osint_states import OSINTStates
from keyboards.inline import get_cancel_keyboard, get_main_menu_keyboard
from config import get_tool_path

router = Router()

EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\.\-]+\.[a-zA-Z]{2,}$")

@router.callback_query(F.data == "menu_email")
async def start_email_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OSINTStates.waiting_for_email)
    await callback.message.edit_text(
        "✉️ <b>Email bo‘yicha OSINT tekshiruvi</b>\n\n"
        "Tekshirmoqchi bo‘lgan elektron pochta manzilini yuboring:\n"
        "<i>Masalan: <code>target@gmail.com</code></i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(OSINTStates.waiting_for_email, F.text)
async def process_email_search(message: Message, state: FSMContext):
    raw_text = message.text.strip()
    if raw_text.startswith("/"):
        return

    email = raw_text.lower()

    # Email formatini tekshirish
    if not EMAIL_REGEX.match(email):
        await message.answer(
            "⚠️ <b>Noto‘g‘ri email formati!</b>\n"
            "Iltimos, to‘g‘ri elektron pochta manzilini kiriting (masalan: <code>user@example.com</code>).",
            reply_markup=get_cancel_keyboard()
        )
        return

    status_msg = await message.answer(
        f"🔍 <b>{email}</b> bo‘yicha 120+ internet xizmatlarida ro‘yxatdan o‘tganlik holati tekshirilmoqda...\n"
        f"⏳ Iltimos kuting, bu 15-30 soniya vaqt olishi mumkin..."
    )

    holehe_cmd = get_tool_path("holehe")
    created_csv_files = []
    report_file = f"email_{email.replace('@', '_at_')}.txt"

    try:
        # Xavfsiz subprocess (create_subprocess_exec orqali)
        proc = await asyncio.create_subprocess_exec(
            holehe_cmd,
            email,
            "--csv",
            "--no-color",
            "--no-clear",
            "--timeout", "10",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await proc.communicate()
        raw_output = stdout.decode("utf-8", errors="ignore")

        # Yaratilgan CSV fayllarni qidirish
        csv_pattern = f"holehe_*_{email}_results.csv"
        matched_csvs = glob.glob(csv_pattern)
        created_csv_files.extend(matched_csvs)

        registered_services = []

        if matched_csvs:
            latest_csv = matched_csvs[0]
            with open(latest_csv, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exists = str(row.get("exists", "")).strip().lower()
                    if exists == "true":
                        name = row.get("name", "Noma'lum")
                        domain = row.get("domain", "")
                        recovery = row.get("emailrecovery", "")
                        phone = row.get("phoneNumber", "")
                        details = []
                        if domain:
                            details.append(domain)
                        if recovery:
                            details.append(f"Qayta tiklash pochtasi: {recovery}")
                        if phone:
                            details.append(f"Telefon: {phone}")

                        detail_str = f" ({', '.join(details)})" if details else ""
                        registered_services.append(f"• <b>{name.title()}</b>{detail_str}")
        else:
            # CSV topilmasa, stdout natijalaridan saralash
            for line in raw_output.splitlines():
                line_str = line.strip()
                if "[+]" in line_str and "Email used" not in line_str:
                    clean = line_str.replace("[+]", "").strip()
                    if clean:
                        registered_services.append(f"• {clean}")

        if registered_services:
            summary = (
                f"✅ <b>{email}</b> quyidagi <b>{len(registered_services)}</b> ta xizmatda ro‘yxatdan o‘tgan:\n\n"
            )
            summary += "\n".join(registered_services[:30])

            if len(registered_services) > 30:
                summary += f"\n\n<i>...va yana {len(registered_services) - 30} ta xizmat to‘liq hisobot faylida.</i>"

            # Hisobot faylini yozish
            with open(report_file, "w", encoding="utf-8") as rf:
                rf.write(f"EMAIL OSINT HISOBOTI: {email}\n")
                rf.write(f"Topilgan xizmatlar soni: {len(registered_services)}\n\n")
                for item in registered_services:
                    clean_item = item.replace("• ", "").replace("<b>", "").replace("</b>", "")
                    rf.write(f"- {clean_item}\n")

            await status_msg.edit_text(summary)

            if os.path.exists(report_file):
                doc = FSInputFile(path=report_file, filename=f"holehe_{email}.txt")
                await message.answer_document(doc, caption=f"📄 {email} bo‘yicha to‘liq hisobot")
        else:
            await status_msg.edit_text(
                f"❌ <b>{email}</b> manzili bo‘yicha hech qanday ochiq ro‘yxatdan o‘tgan platformalar topilmadi."
            )

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Xatolik yuz berdi:\n<code>{str(e)}</code>")

    finally:
        # CSV va hisobot fayllarini tozalash
        for cf in created_csv_files:
            if os.path.exists(cf):
                try:
                    os.remove(cf)
                except OSError:
                    pass
        if os.path.exists(report_file):
            try:
                os.remove(report_file)
            except OSError:
                pass

        await state.clear()
        await message.answer("Bosh menyuga qaytish uchun tugmani bosing:", reply_markup=get_main_menu_keyboard())
