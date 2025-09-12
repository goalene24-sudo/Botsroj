from telethon import TelegramClient
from datetime import datetime
import config
import logging
from database import engine, init_db  # استيراد engine وinit_db من database.py
from models import Base  # استيراد Base من models.py

StartTime = datetime.now()

try:
    # --- هذا هو السطر الذي تم تصحيحه ---
    # لقد استبدلنا None باسم جلسة وليكن 'saruj_bot'
    client = TelegramClient('saruj_bot', config.API_ID, config.API_HASH)
    # ------------------------------------
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    logging.critical(f"!! خطأ فادح عند تهيئة البوت: {e}", exc_info=True)
    exit(1)

async def main():
    await init_db()  # استدعاء دالة init_db من database.py لإنشاء الجداول
    await client.start()
    print("البوت يعمل الآن...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
