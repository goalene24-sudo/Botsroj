from telethon import TelegramClient
from datetime import datetime
import config
import logging
from database import engine  # استيراد engine من database.py
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

async def create_tables():
    """إنشاء جميع الجداول تلقائيًا إذا لم تكن موجودة."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(">> تم إنشاء الجداول بنجاح.")

async def main():
    await create_tables()  # إنشاء الجداول قبل بدء البوت
    await client.start()
    print("البوت يعمل الآن...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
