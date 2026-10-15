import os
import io
import asyncio
from PIL import Image
import exifread

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.osint_states import OSINTStates
from keyboards.inline import get_cancel_keyboard, get_main_menu_keyboard

router = Router()

def _convert_dms_to_decimal(dms_tag, ref_tag) -> float | None:
    """
    GPS daraja, daqiqa va soniyalarni o'nlik (decimal) formatga o'tkazish.
    """
    try:
        vals = dms_tag.values
        d = float(vals[0].num) / float(vals[0].den)
        m = float(vals[1].num) / float(vals[1].den)
        s = float(vals[2].num) / float(vals[2].den)
        decimal = d + (m / 60.0) + (s / 3600.0)

        ref = str(ref_tag).strip().upper()
        if ref in ["S", "W"]:
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None

def extract_image_exif(image_path: str) -> dict:
    """
    Rasm faylidan to'liq EXIF va GPS ma'lumotlarini ajratib olish.
    """
    result = {
        "dimensions": None,
        "camera_make": None,
        "camera_model": None,
        "software": None,
        "datetime": None,
        "lens": None,
        "iso": None,
        "exposure": None,
        "f_number": None,
        "gps_latitude": None,
        "gps_longitude": None,
        "gps_altitude": None,
        "google_maps": None,
        "raw_tags_count": 0
    }

    # 1. Pillow orqali o'lchamlarini olish
    try:
        with Image.open(image_path) as img:
            result["dimensions"] = f"{img.width}x{img.height} piksel ({img.format})"
    except Exception:
        pass

    # 2. ExifRead orqali chuqur metama'lumotlarni o'qish
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=True)
            result["raw_tags_count"] = len(tags)

            if "Image Make" in tags:
                result["camera_make"] = str(tags["Image Make"]).strip()
            if "Image Model" in tags:
                result["camera_model"] = str(tags["Image Model"]).strip()
            if "Image Software" in tags:
                result["software"] = str(tags["Image Software"]).strip()
            if "EXIF DateTimeOriginal" in tags:
                result["datetime"] = str(tags["EXIF DateTimeOriginal"]).strip()
            elif "Image DateTime" in tags:
                result["datetime"] = str(tags["Image DateTime"]).strip()
            if "EXIF LensModel" in tags:
                result["lens"] = str(tags["EXIF LensModel"]).strip()
            if "EXIF ISOSpeedRatings" in tags:
                result["iso"] = str(tags["EXIF ISOSpeedRatings"]).strip()
            if "EXIF ExposureTime" in tags:
                result["exposure"] = str(tags["EXIF ExposureTime"]).strip()
            if "EXIF FNumber" in tags:
                result["f_number"] = str(tags["EXIF FNumber"]).strip()

            # GPS koordinatalarini hisoblash
            lat_tag = tags.get("GPS GPSLatitude")
            lat_ref = tags.get("GPS GPSLatitudeRef")
            lon_tag = tags.get("GPS GPSLongitude")
            lon_ref = tags.get("GPS GPSLongitudeRef")

            if lat_tag and lat_ref and lon_tag and lon_ref:
                lat = _convert_dms_to_decimal(lat_tag, lat_ref)
                lon = _convert_dms_to_decimal(lon_tag, lon_ref)
                if lat is not None and lon is not None:
                    result["gps_latitude"] = lat
                    result["gps_longitude"] = lon
                    result["google_maps"] = f"https://www.google.com/maps?q={lat},{lon}"

            if "GPS GPSAltitude" in tags:
                try:
                    alt_val = tags["GPS GPSAltitude"].values[0]
                    alt = float(alt_val.num) / float(alt_val.den)
                    result["gps_altitude"] = f"{round(alt, 1)} metr"
                except Exception:
                    pass

    except Exception:
        pass

    return result

@router.callback_query(F.data == "menu_metadata")
async def start_metadata_analysis(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OSINTStates.waiting_for_image)
    await callback.message.edit_text(
        "📷 <b>Rasm EXIF va GPS Metama'lumotlari tahlili</b>\n\n"
        "Tahlil qilmoqchi bo‘lgan rasmni yuboring.\n\n"
        "💡 <i>Eslatma: Telegram odatiy 'Rasm (Photo)' qilib yuborilganda uning metama'lumotlarini avtomatik tozalab tashlaydi. "
        "Kamera va GPS ma'lumotlarini to'liq olish uchun rasmni <b>Hujjat (File/Document)</b> sifatida (siqilmagan holda) yuborish tavsiya etiladi.</i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(OSINTStates.waiting_for_image, F.photo | F.document)
async def process_image_metadata(message: Message, state: FSMContext, bot: Bot):
    status_msg = await message.answer("⏳ Rasm yuklab olinmoqda va EXIF/GPS tahlil qilinmoqda...")

    temp_path = f"temp_meta_{message.from_user.id}_{message.message_id}.jpg"

    try:
        # Faylni Telegram'dan yuklab olish
        if message.photo:
            # Eng yuqori sifatli rasmni olish
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        file_obj = await bot.get_file(file_id)
        await bot.download_file(file_obj.file_path, destination=temp_path)

        # Metama'lumotlarni ajratish
        exif_data = await asyncio.to_thread(extract_image_exif, temp_path)

        lines = ["🔍 <b>Rasm metama'lumotlari hisoboti:</b>\n"]

        if exif_data["dimensions"]:
            lines.append(f"📐 <b>O‘lchami:</b> {exif_data['dimensions']}")

        # Qurilma
        camera_info = []
        if exif_data["camera_make"]:
            camera_info.append(exif_data["camera_make"])
        if exif_data["camera_model"]:
            camera_info.append(exif_data["camera_model"])

        if camera_info:
            lines.append(f"📱 <b>Qurilma (Kamera):</b> {' '.join(camera_info)}")
        if exif_data["lens"]:
            lines.append(f"🔍 <b>Ob’yektiv:</b> {exif_data['lens']}")
        if exif_data["software"]:
            lines.append(f"💻 <b>Dastur:</b> {exif_data['software']}")
        if exif_data["datetime"]:
            lines.append(f"📅 <b>Suratga olingan vaqt:</b> <code>{exif_data['datetime']}</code>")

        # Kamera parametrlari
        shoot_params = []
        if exif_data["iso"]:
            shoot_params.append(f"ISO {exif_data['iso']}")
        if exif_data["exposure"]:
            shoot_params.append(f"{exif_data['exposure']}s")
        if exif_data["f_number"]:
            shoot_params.append(f"f/{exif_data['f_number']}")
        if shoot_params:
            lines.append(f"⚙️ <b>Surat parametrlari:</b> {', '.join(shoot_params)}")

        # GPS ma'lumotlari
        has_gps = False
        lat = exif_data["gps_latitude"]
        lon = exif_data["gps_longitude"]

        if lat is not None and lon is not None:
            has_gps = True
            lines.append("\n📍 <b>GPS Geolokatsiya ma'lumotlari:</b>")
            lines.append(f"• Kenglik (Latitude): <code>{lat}</code>")
            lines.append(f"• Uzunlik (Longitude): <code>{lon}</code>")
            if exif_data["gps_altitude"]:
                lines.append(f"• Balandlik (Altitude): {exif_data['gps_altitude']}")
            lines.append(f"🗺 <a href=\"{exif_data['google_maps']}\">Google Maps orqali xaritada ko‘rish</a>")

        if exif_data["raw_tags_count"] == 0 and not exif_data["dimensions"]:
            lines.append("\n⚠️ <i>Ushbu rasmda hech qanday EXIF metama'lumotlari topilmadi. (Telegram yoki rasm muharriri tomonidan tozalangan bo‘lishi mumkin).</i>")
        elif not has_gps and not camera_info and not exif_data["datetime"]:
            lines.append("\nℹ️ <i>Asosiy EXIF yorliqlari (GPS/Kamera) mavjud emas yoki o‘chirilgan.</i>")

        await status_msg.edit_text("\n".join(lines), disable_web_page_preview=True)

        # Agar GPS koordinatalari aniqlansa, Telegram orqali xaritada nuqtani ham yuboramiz!
        if has_gps:
            await message.answer_location(latitude=lat, longitude=lon)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Tahlil jarayonida xatolik yuz berdi:\n<code>{str(e)}</code>")

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        await state.clear()
        await message.answer("Bosh menyuga qaytish uchun tugmani bosing:", reply_markup=get_main_menu_keyboard())

@router.message(OSINTStates.waiting_for_image)
async def process_invalid_image_input(message: Message):
    await message.answer(
        "⚠️ Iltimos, tahlil qilish uchun rasm yuboring (fayl yoki rasm formatida).",
        reply_markup=get_cancel_keyboard()
    )
