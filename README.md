# 🕵️‍♂️ Professional Modulli OSINT Telegram Bot (Aiogram 3)

Ushbu loyiha shaxsiy kiberxavfsizlik va OSINT (Open Source Intelligence) tadqiqotlari uchun mo‘ljallangan, to‘liq asinxron va modulli arxitekturaga ega bo‘lgan Telegram bot hisoblanadi.

---

## 📁 Loyihaning Papkalar Tuzilishi (Project Structure)

```text
osint bot/
│
├── .env                  # Maxfiy tokenlar va admin sozlamalari
├── .env.example          # Namuna sozlama fayli
├── .gitignore            # Git e'tibor bermaydigan fayllar (venv, .env, hisobotlar)
├── requirements.txt      # Barcha kerakli Python kutubxonalari
├── README.md             # Loyiha hujjatlari va yo'riqnoma
├── config.py             # Muhit o'zgaruvchilari va CLI vositalari yo'llari
├── main.py               # Botning asosiy kirish nuqtasi, dispatcher va routerlar
│
├── middlewares/          # Telegram yangilanishlarini filtrlash
│   ├── __init__.py
│   └── auth.py           # Faqat ALLOWED_USER_ID uchun o'tkazuvchi xavfsizlik filtri
│
├── keyboards/            # Inline tugmalar
│   ├── __init__.py
│   └── inline.py         # Asosiy menyu va bekor qilish tugmalari
│
├── states/               # FSM (Finite State Machine) holatlari
│   ├── __init__.py
│   └── osint_states.py   # Har bir modul uchun qadam-baqadam holatlar
│
└── modules/              # Alohida OSINT modullari
    ├── __init__.py
    ├── username.py       # Sherlock CLI: 400+ platformalardan username qidirish
    ├── email_osint.py    # Holehe CLI: Email orqali xizmatlarni aniqlash
    ├── dorking.py        # DDGS: Ism-familiya bo'yicha Google/DDG Dorking
    ├── metadata.py       # Pillow & ExifRead: Rasm EXIF, kamera va GPS tahlili
    └── network.py        # DNS & WHOIS: Domen va IP manzil tahlili
```

---

## 🛡️ Xavfsizlik va Kirish Nazorati

1. **Whitelisting (Faqat bitta admin):**
   - `middlewares/auth.py` orqali Aiogram 3 ning `outer_middleware` darajasida tekshiriladi.
   - Begona foydalanuvchilarning barcha xabarlari va tugma bosishlari **butunlay eʼtiborsiz qoldiriladi** (hech qanday ma'lumot yoki rad javobi ham berilmaydi).
2. **Subprocess xavfsizligi:**
   - Tashqi CLI buyruqlar (`sherlock`, `holehe`) `asyncio.create_subprocess_exec` orqali parametrlangan holda bajariladi. Bu shell injection (`sh` / `bash` / `cmd` in'yeksiyasi) xavfini 100% bartaraf etadi.

---

## 🚀 O‘rnatish va Ishga Tushirish

### 1. Virtual muhitni faollashtirish:
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\activate
  ```
- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### 2. Kutubxonalarni o‘rnatish:
```bash
pip install -r requirements.txt
```

### 3. `.env` faylini sozlash:
`.env` faylida quyidagi ma'lumotlar mavjudligini tekshiring:
```env
BOT_TOKEN=your_telegram_bot_token_here
ALLOWED_USER_ID=your_telegram_user_id_here
```

### 4. Botni ishga tushirish:
```powershell
python main.py
```
yoki to‘g‘ridan-to‘g‘ri venv orqali:
```powershell
.\venv\Scripts\python.exe main.py
```
