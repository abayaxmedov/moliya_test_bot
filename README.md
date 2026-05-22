# Quiz Test Bot

Bu bot `Davlat xususiy sheriklik.txt` faylidagi 150 ta savolni Telegram quiz sifatida yuboradi. Har bir savol uchun javob variantlari random tartibda keladi va 30 soniya tugashi bilan bot avtomatik keyingi savolga o'tadi.

Savollar 8 ta guruhga bo'lingan. Foydalanuvchi `/start` bosganda bot qaysi guruh savollarini bajarmoqchiligini so'raydi va tanlangan guruh savollarini yuboradi.

## O'rnatish

1. Python 3.10+ o'rnating.
2. Kutubxonalarni o'rnating:
   ```
   pip install -r requirements.txt
   ```

## Ishga tushirish

1. Telegram Bot Father orqali bot yarating va token oling.
2. Environment variable o'rnating:
   ```
   export BOT_TOKEN=your_bot_token_here
   ```
3. Botni ishga tushiring:
   ```
   python3 main.py
   ```

## Fayl tuzilmasi

- `config.py`: Konfiguratsiya
- `quiz_parser.py`: TXT faylni parse qilish
- `quiz_logic.py`: Savollarni tanlash va variantlarni random qilish
- `handlers.py`: Aiogram handlerlari va quiz oqimi
- `main.py`: Asosiy fayl
- `requirements.txt`: Kutubxonalar
- `Davlat xususiy sheriklik.txt`: Savollar fayli
- `bot.py`: Eski tajriba variant, joriy ishga tushirish yo'li emas

Savollar faylida to'g'ri javob `#` belgisi bilan boshlanishi mumkin. Agar `#` bo'lmasa, bot eski formatga mos ravishda birinchi variantni to'g'ri javob deb oladi.

## Ishlatish

- Botga /start yuboring.
- Botdan kerakli guruhni tanlang.
- Bot tanlangan guruh savollarini quiz poll sifatida yuboradi.
- Har bir savolda 30 soniya vaqt bor.
- Foydalanuvchi javob bersa darhol, javob bermasa 30 soniyadan keyin avtomatik keyingi savol keladi.
