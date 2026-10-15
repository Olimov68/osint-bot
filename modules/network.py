import re
import socket
import asyncio
from urllib.parse import urlparse
import dns.resolver
import whois

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.osint_states import OSINTStates
from keyboards.inline import get_cancel_keyboard, get_main_menu_keyboard

router = Router()

def clean_target(input_text: str) -> str:
    """
    Kiritilgan URL yoki domenni toza domen/IP ko'rinishiga keltiradi.
    """
    text = input_text.strip().lower()
    if not text.startswith("http://") and not text.startswith("https://"):
        text = "http://" + text

    try:
        parsed = urlparse(text)
        netloc = parsed.netloc.split(":")[0]  # portni olib tashlash
        return netloc.strip()
    except Exception:
        return input_text.strip().lower()

def perform_dns_lookup(domain: str) -> dict:
    """
    Domen bo'yicha asosiy DNS yozuvlarini tahlil qilish (A, AAAA, MX, NS, TXT, CNAME).
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 3.0

    records = {}
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]

    for rtype in record_types:
        try:
            answers = resolver.resolve(domain, rtype)
            values = [r.to_text() for r in answers]
            if values:
                records[rtype] = values
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.Timeout):
            continue
        except Exception:
            continue

    return records

def perform_whois_lookup(domain: str) -> dict:
    """
    Domen bo'yicha WHOIS ma'lumotlarini olish.
    """
    try:
        w = whois.whois(domain)
        # Natijalarni tozalash (ba'zida ro'yxat bo'ladi)
        def format_date(val):
            if isinstance(val, list):
                return str(val[0])
            return str(val) if val else "Noma'lum"

        return {
            "registrar": w.registrar or "Noma'lum",
            "creation_date": format_date(w.creation_date),
            "expiration_date": format_date(w.expiration_date),
            "updated_date": format_date(w.updated_date),
            "country": w.country or "Noma'lum",
            "org": w.org or "Noma'lum",
            "name_servers": list(set(w.name_servers)) if isinstance(w.name_servers, list) else (w.name_servers or [])
        }
    except Exception as e:
        return {"error": str(e)}

@router.callback_query(F.data == "menu_network")
async def start_network_analysis(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OSINTStates.waiting_for_domain)
    await callback.message.edit_text(
        "🌐 <b>Domen va IP manzil tahlili (WHOIS / DNS)</b>\n\n"
        "Tahlil qilmoqchi bo‘lgan domen yoki IP manzilni kiriting:\n"
        "<i>Masalan: <code>example.com</code>, <code>google.com</code> yoki <code>1.1.1.1</code></i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(OSINTStates.waiting_for_domain, F.text)
async def process_network_analysis(message: Message, state: FSMContext):
    raw_text = message.text.strip()
    if raw_text.startswith("/"):
        return

    domain = clean_target(raw_text)

    if not domain or len(domain) < 3 or " " in domain:
        await message.answer(
            "⚠️ Iltimos, to‘g‘ri formatdagi domen yoki IP manzil kiriting.",
            reply_markup=get_cancel_keyboard()
        )
        return

    status_msg = await message.answer(
        f"🔍 <b>{domain}</b> bo‘yicha DNS va WHOIS tahlili amalga oshirilmoqda...\n"
        f"⏳ Iltimos kuting..."
    )

    try:
        # Asinxron ravishda DNS va WHOIS so'rovlarini parallel bajarish
        dns_task = asyncio.to_thread(perform_dns_lookup, domain)
        whois_task = asyncio.to_thread(perform_whois_lookup, domain)

        dns_results, whois_results = await asyncio.gather(dns_task, whois_task)

        lines = [f"🌐 <b>TARMOQ HISOBOTI: {domain}</b>\n"]

        # 1. DNS ma'lumotlari
        lines.append("📡 <b>DNS Yozuvlari:</b>")
        if dns_results:
            if "A" in dns_results:
                lines.append(f"• <b>IPv4 (A):</b> {', '.join(dns_results['A'])}")
            if "AAAA" in dns_results:
                lines.append(f"• <b>IPv6 (AAAA):</b> {', '.join(dns_results['AAAA'])}")
            if "MX" in dns_results:
                lines.append("• <b>Pochta serverlari (MX):</b>")
                for mx in dns_results["MX"][:4]:
                    lines.append(f"   ↳ <code>{mx}</code>")
            if "NS" in dns_results:
                lines.append("• <b>Name Servers (NS):</b>")
                for ns in dns_results["NS"][:4]:
                    lines.append(f"   ↳ <code>{ns}</code>")
            if "TXT" in dns_results:
                lines.append("• <b>TXT yozuvlari:</b>")
                for txt in dns_results["TXT"][:3]:
                    clean_txt = txt.strip('"')[:70]
                    lines.append(f"   ↳ <code>{clean_txt}</code>")
            if "CNAME" in dns_results:
                lines.append(f"• <b>CNAME:</b> {', '.join(dns_results['CNAME'])}")
        else:
            lines.append("<i>Hech qanday ochiq DNS yozuvlari aniqlanmadi.</i>")

        lines.append("")

        # 2. WHOIS ma'lumotlari
        lines.append("📋 <b>WHOIS Ma'lumotlari:</b>")
        if "error" not in whois_results:
            lines.append(f"• <b>Registrar:</b> {whois_results['registrar']}")
            lines.append(f"• <b>Yaratilgan sana:</b> <code>{whois_results['creation_date']}</code>")
            lines.append(f"• <b>Amal qilish muddati:</b> <code>{whois_results['expiration_date']}</code>")
            if whois_results["updated_date"] != "Noma'lum":
                lines.append(f"• <b>Oxirgi yangilanish:</b> <code>{whois_results['updated_date']}</code>")
            if whois_results["country"] != "Noma'lum":
                lines.append(f"• <b>Mamlakat:</b> {whois_results['country']}")
            if whois_results["org"] != "Noma'lum":
                lines.append(f"• <b>Tashkilot:</b> {whois_results['org']}")
        else:
            lines.append(f"<i>WHOIS so‘rovi muvaffaqiyatsiz tugadi (Domen yopiq yoki himoyalangan bo‘lishi mumkin).</i>")

        final_text = "\n".join(lines)
        if len(final_text) > 4000:
            final_text = final_text[:3950] + "\n..."

        await status_msg.edit_text(final_text)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Xatolik yuz berdi:\n<code>{str(e)}</code>")

    finally:
        await state.clear()
        await message.answer("Bosh menyuga qaytish uchun tugmani bosing:", reply_markup=get_main_menu_keyboard())
