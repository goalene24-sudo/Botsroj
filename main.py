import logging
import importlib
import sys
from datetime import datetime
import asyncio
import os
from threading import Thread
from flask import Flask

from plugins.events import start_dhikr_task

# --- علامة اختبار حاسمة ---
print("="*50)
print(f"--- نسخة الاختبار بتاريخ: {datetime.now()} ---")
print(">>> يتم الآن محاولة تشغيل ملف main.py المحدث <<<")
print("="*50)

from bot import client
from plugins import ALL_MODULES
import config
from database import init_db

# --- الإعدادات الأساسية ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# --- تعديل مستوى تسجيل sqlalchemy لتقليل الرسائل ---
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


# --- (جديد) إعداد خادم الويب المصغر لخطة Koyeb المجانية ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running successfully!"

def run_web_server():
    # Koyeb تقوم بتعيين متغير PORT تلقائيًا
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


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
        # --- تهيئة قاعدة البيانات وإنشاء الجداول ---
        LOGGER.info(">> يتم الآن تهيئة قاعدة البيانات (إنشاء الجداول إذا لم تكن موجودة)... <<")
        await init_db()
        LOGGER.info(">> اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        
        # --- (جديد) بدء مهمة الأذكار الدورية في الخلفية ---
        LOGGER.info(">> يتم الآن بدء مهمة الأذكار الدورية... <<")
        asyncio.create_task(start_dhikr_task())
        
        LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
        await client.run_until_disconnected()
    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    # --- (جديد) بدء تشغيل خادم الويب في خيط منفصل ---
    LOGGER.info(">> يتم الآن بدء تشغيل خادم الويب (Health Check)... <<")
    web_thread = Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    LOGGER.info(">> خادم الويب يعمل الآن في الخلفية. <<")

    # --- بدء تشغيل البوت نفسه ---
    client.loop.run_until_complete(main())
