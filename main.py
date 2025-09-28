import logging
import importlib
import sys
from datetime import datetime
import asyncio
# --- (جديد) استيراد المكتبات اللازمة للخادم الوهمي ---
import threading
import http.server
import socketserver
import os

# --- استيراد المهمة الجديدة ---
from plugins.auto_messages import scheduler_task

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
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# =========================================================
# | START OF NEW CODE | بداية الكود الجديد (الباب الوهمي)   |
# =========================================================
def start_health_check_server():
    """
    تقوم ببدء خادم ويب بسيط جداً في الخلفية للرد على فحص الصحة الخاص بالمنصات.
    """
    # المنصات توفر البورت في متغير البيئة PORT، وإذا لم يكن موجوداً نستخدم 8000
    PORT = int(os.environ.get("PORT", 8000))
    Handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            LOGGER.info(f"✅ | الخادم الوهمي (Health Check) يعمل على البورت {PORT}")
            httpd.serve_forever()
    except Exception as e:
        LOGGER.error(f"!! فشل تشغيل الخادم الوهمي: {e}", exc_info=True)
# =========================================================
# | END OF NEW CODE | نهاية الكود الجديد                      |
# =========================================================

# --- تحميل كل الإضافات ---
LOGGER.info(">> يتم الآن تحميل كل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        LOGGER.info(f"  - تم تحميل الوحدة: {module}")
    except Exception as e:
        LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)


# --- دالة التشغيل الرئيسية ---
async def main():
    try:
        # --- (جديد) بدء تشغيل الخادم الوهمي في thread منفصل ---
        LOGGER.info(">> يتم الآن بدء تشغيل خادم فحص الصحة في الخلفية... <<")
        health_thread = threading.Thread(target=start_health_check_server, daemon=True)
        health_thread.start()

        # --- تهيئة قاعدة البيانات وإنشاء الجداول ---
        LOGGER.info(">> يتم الآن تهيئة قاعدة البيانات (إنشاء الجداول إذا لم تكن موجودة)... <<")
        await init_db()
        LOGGER.info(">> اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        # --- بدء تشغيل البوت والاتصال ---
        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        
        # --- (تم التعديل هنا) بدء المهمة الدورية الجديدة ---
        LOGGER.info(">> يتم الآن بدء مهمة الرسائل الدورية (الجدولة)... <<")
        asyncio.create_task(scheduler_task())
        
        LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
        await client.run_until_disconnected()

    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    # هذا السطر يشغل الحلقة الرئيسية غير المتزامنة
    client.loop.run_until_complete(main())
