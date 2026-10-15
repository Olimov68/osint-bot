import asyncio
import html
import os
from typing import Tuple, Optional

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from states.osint_states import OSINTStates
from keyboards.inline import get_cancel_keyboard

router = Router()

async def run_dorking(query_name: str) -> Tuple[str, Optional[str]]:
    """
    Berilgan ism-familiya bo'yicha Dorking qidiruvini amalga oshiradi,
    natijalarni to'liq .txt faylga yozadi va chat uchun ixcham xabar tayyorlaydi.
    """
    def _search():
        # Dorking shabloni
        dork = f'"{query_name}" (site:linkedin.com OR site:instagram.com OR site:facebook.com OR site:t.me OR site:github.com)'
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(dork, max_results=15))
        except Exception:
            # Fallback agar context manager bilan muammo bo'lsa
            ddgs = DDGS()
            return list(ddgs.text(dork, max_results=15))

    try:
        results = await asyncio.to_thread(_search)
        if not results:
            return f"❌ <b>{html.escape(query_name)}</b> bo‘yicha hech narsa topilmadi.", None

        # Xavfsiz fayl nomi yasash
        clean_name = "".join(c for c in query_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        if not clean_name:
            clean_name = "target"
        file_path = f"dorking_{clean_name}.txt"

        # 1. Barcha natijalarni to'liq .txt faylga yozamiz
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"========================================\n")
            f.write(f"  OSINT DORKING HISOBOTI: {query_name}\n")
            f.write(f"========================================\n\n")
            for idx, item in enumerate(results, 1):
                title = item.get("title", "Havola")
                href = item.get("href", "")
                body = item.get("body", "")
                f.write(f"[{idx}] {title}\n")
                f.write(f"Havola: {href}\n")
                f.write(f"Ma'lumot: {body}\n")
                f.write("-" * 40 + "\n")

        # 2. Telegram chatga faqat dastlabki 4 ta asosiy natijani chiqaramiz (limitdan oshib ketmaydi)
        summary_text = f"🔎 <b>{html.escape(query_name)}</b> bo‘yicha <b>{len(results)}</b> ta natija topildi:\n\n"
        for idx, item in enumerate(results[:4], 1):
            title = html.escape(item.get("title", "Havola"))
            href = item.get("href", "")
            summary_text += f"{idx}. <a href='{href}'>{title}</a>\n"

        summary_text += f"\n📄 <i>Barcha to‘liq maʼlumotlar pastdagi faylga yuklandi.</i>"

        return summary_text, file_path

    except Exception as e:
        return f"⚠️ Dorking qidiruvida xatolik: {html.escape(str(e))}", None

@router.callback_query(F.data == "menu_dorking")
async def start_dorking(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OSINTStates.waiting_for_dork)
    await callback.message.edit_text(
        "🔎 <b>Ism-familiya bo‘yicha Google / Dorking qidiruvi</b>\n\n"
        "Qidirmoqchi bo‘lgan shaxsning ism va familiyasini (yoki kalit so‘zni) kiriting:\n"
        "<i>Masalan: <code>Pavel Durov</code> yoki <code>John Doe</code></i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()
