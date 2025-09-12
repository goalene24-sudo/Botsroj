from telethon import TelegramClient
from datetime import datetime
import config
import logging
from database import engine, init_db  # استيراد engine وinit_db من database.py
from models import Base  # استيراد Base من models.py
import importlib  # لتحميل الوحدات الديناميكية

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

async def load_plugins():
    """تحميل الوحدات الإضافية (plugins)"""
    plugins_dir = "plugins"
    for plugin in [p for p in os.listdir(plugins_dir) if p.endswith(".py") and not p.startswith("__")]:
        try:
            plugin_name = plugin[:-3]  # إزالة .py
            importlib.import_module(f"{plugins_dir}.{plugin_name}")
            logging.info(f"تم تحميل الوحدة {plugin_name} بنجاح.")
        except Exception as e:
            logging.error(f"!! فشل تحميل الوحدة {plugin}: {e}", exc_info=True)

async def main():
    await init_db()  # استدعاء دالة init_db من database.py لإنشاء الجداول
    await client.start()
    await load_plugins()  # تحميل الوحدات بعد بدء البوت
    print("البوت يعمل الآن...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import os
    asyncio.run(main())
