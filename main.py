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


# --- تحميل كل الإضافات ---
LOGGER.info(">> يتم الآن تحميل كل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        LOGGER.info(f"  - تم تحميل الوحدة: {module}")
    except Exception as e:
        LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)


# --- دالة التشغيل الرئيسية ---
async def main():
    try:
        # ===================================================================
        # | START OF FINAL FIX | بداية الإصلاح النهائي                      |
        # ===================================================================
        # 1. إنشاء المحرك وتخزينه في متغير محلي
        DB_NAME = "surooj.db"
        DB_URI = f"sqlite+aiosqlite:///{DB_NAME}?check_same_thread=False"
        local_engine = create_async_engine(DB_URI, echo=False, poolclass=NullPool)
        
        # 2. إنشاء صانع الجلسات باستخدام المحرك المحلي ووضعه في وحدة قاعدة البيانات
        #    حتى تتمكن الملفات الأخرى من استخدامه.
        database.AsyncDBSession = async_sessionmaker(
            bind=local_engine, expire_on_commit=False, class_=AsyncSession
        )
        # ===================================================================
        # | END OF FINAL FIX | نهاية الإصلاح النهائي                         |
        # ===================================================================

        # --- تهيئة قاعدة البيانات وإنشاء الجداول ---
        LOGGER.info(">> يتم الآن تهيئة قاعدة البيانات (إنشاء الجداول إذا لم تكن موجودة)... <<")
        # 3. تمرير المحرك مباشرة إلى الدالة لضمان عدم حدوث خطأ
        await database.init_db(local_engine)
        LOGGER.info(">> اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        
        # --- بدء مهمة الأذكار الدورية في الخلفية ---
        LOGGER.info(">> يتم الآن بدء مهمة الأذكار الدورية... <<")
        asyncio.create_task(start_dhikr_task())
        
        LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
        await client.run_until_disconnected()
    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    asyncio.run(main())
