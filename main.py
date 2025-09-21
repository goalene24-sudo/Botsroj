import logging
import importlib
import sys
from datetime import datetime
import asyncio
from plugins.events import start_dhikr_task

# استيراد الأدوات اللازمة لإنشاء المحرك
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
# سنقوم باستيراد الوحدة كاملة
import database


# --- علامة اختبار حاسمة ---
print("="*50)
print(f"--- نسخة الاختبار بتاريخ: {datetime.now()} ---")
print(">>> يتم الآن محاولة تشغيل ملف main.py المحدث <<<")
print("="*50)

from bot import client
from plugins import ALL_MODULES
import config


# --- الإعدادات الأساسية ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# --- تعديل مستوى تسجيل sqlalchemy لتقليل الرسائل ---
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


# --- دالة التشغيل الرئيسية ---
async def main():
    try:
        # --- (الخطوة 1 - تم تعديل الترتيب) تهيئة قاعدة البيانات أولاً ---
        LOGGER.info(">> [1/4] يتم الآن تهيئة محرك قاعدة البيانات... <<")
        DB_NAME = "surooj.db"
        DB_URI = f"sqlite+aiosqlite:///{DB_NAME}?check_same_thread=False"
        local_engine = create_async_engine(DB_URI, echo=False, poolclass=NullPool)
        
        database.AsyncDBSession = async_sessionmaker(
            bind=local_engine, expire_on_commit=False, class_=AsyncSession
        )

        await database.init_db(local_engine)
        LOGGER.info(">> [1/4] اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        # --- (الخطوة 2 - تم تعديل الترتيب) تحميل الإضافات ثانياً ---
        LOGGER.info(">> [2/4] يتم الآن تحميل كل الوحدات... <<")
        for module in ALL_MODULES:
            try:
                importlib.import_module(module)
                LOGGER.info(f"  - تم تحميل الوحدة: {module}")
            except Exception as e:
                LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)
        LOGGER.info(">> [2/4] اكتمل تحميل جميع الوحدات. <<")

        # --- (الخطوة 3) تسجيل الدخول ---
        LOGGER.info(">> [3/4] يتم الآن تسجيل الدخول... <<")
        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        LOGGER.info(f">> [3/4] تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        
        # --- (الخطوة 4) بدء المهام وتشغيل البوت ---
        LOGGER.info(">> [4/4] يتم الآن بدء المهام الإضافية... <<")
        asyncio.create_task(start_dhikr_task())
        
        LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
        await client.run_until_disconnected()

    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    asyncio.run(main())
