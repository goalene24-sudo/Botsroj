from telethon import TelegramClient
from datetime import datetime
import config
import logging
from database import engine, init_db  # استيراد engine وinit_db من database.py
from models import Base  # استيراد Base من models.py
import importlib  # لتحميل الوحدات الديناميكية
import os  # للتعامل مع الملفات

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

StartTime = datetime.now()

try:
    # --- هذا هو السطر الذي تم تصحيحه ---
    client = TelegramClient('saruj_bot', config.API_ID, config.API_HASH)
    logger.info("تم تهيئة العميل بنجاح.")
except Exception as e:
    logger.critical(f"!! خطأ فادح عند تهيئة البوت: {e}", exc_info=True)
    exit(1)

async def load_plugins():
    """تحميل الوحدات الإضافية (plugins)"""
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        logger.error(f"مجلد الوحدات {plugins_dir} غير موجود!")
        return
    for plugin in [p for p in os.listdir(plugins_dir) if p.endswith(".py") and not p.startswith("__")]:
        try:
            plugin_name = plugin[:-3]  # إزالة .py
            importlib.import_module(f"{plugins_dir}.{plugin_name}")
            logger.info(f"تم تحميل الوحدة {plugin_name} بنجاح.")
        except Exception as e:
            logger.error(f"!! فشل تحميل الوحدة {plugin}: {e}", exc_info=True)

async def main():
    logger.info("بدء تشغيل البوت...")
    try:
        await init_db()  # استدعاء دالة init_db من database.py لإنشاء الجداول
        logger.info("تم إنشاء الجداول بنجاح.")
    except Exception as e:
        logger.critical(f"فشل إنشاء الجداول: {e}", exc_info=True)
        exit(1)  # إنهاء البرنامج إذا فشل إنشاء الجداول
    
    await client.start()
    logger.info("البوت قد بدأ بنجاح.")
    await load_plugins()  # تحميل الوحدات بعد بدء البوت
    logger.info("البوت يعمل الآن...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
