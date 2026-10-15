import os
import sys
import shutil
from dotenv import load_dotenv

# .env sozlamalarini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("Xatolik: BOT_TOKEN aniqlanmadi! .env faylini tekshiring.")

if not ALLOWED_USER_ID:
    raise ValueError("Xatolik: ALLOWED_USER_ID aniqlanmadi! .env faylini tekshiring.")

def get_tool_path(tool_name: str) -> str:
    """
    Tizimda yoki venv muhitida vosita (sherlock, holehe va h.k.)
    bajariluvchi faylini xavfsiz topish uchun yordamchi funksiya.
    """
    # 1. Tizim PATH orqali
    which_path = shutil.which(tool_name) or shutil.which(f"{tool_name}.exe")
    if which_path:
        return which_path

    # 2. Virtual muhit (Windows)
    venv_tool_win = os.path.join(os.path.dirname(sys.executable), f"{tool_name}.exe")
    if os.path.exists(venv_tool_win):
        return venv_tool_win

    # 3. Virtual muhit (Linux/macOS)
    venv_tool_unix = os.path.join(os.path.dirname(sys.executable), tool_name)
    if os.path.exists(venv_tool_unix):
        return venv_tool_unix

    return tool_name
