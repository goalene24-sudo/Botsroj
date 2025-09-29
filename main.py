import logging
import importlib
import sys
import os
import asyncio
import secrets
from aiohttp import web

# استيرادات البوت الأساسية
from plugins.auto_messages import scheduler_task
from bot import client
from plugins import ALL_MODULES
import config
from database import init_db

# --- الإعدادات الأساسية ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# --- إعدادات Webhook ---
PORT = int(os.environ.get("PORT", 8080)) # تم تغيير البورت الافتراضي إلى 8080 الشائع
SECRET_TOKEN = os.environ.get("SECRET_TOKEN")
if not SECRET_TOKEN:
    SECRET_TOKEN = secrets.token_hex(32)
    LOGGER.warning("لم يتم العثور على SECRET_TOKEN! تم إنشاء رمز مؤقت. يرجى إضافته في Variables.")

# --- تحميل كل الإضافات ---
LOGGER.info(">> يتم الآن تحميل كل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        LOGGER.info(f"  - تم تحميل الوحدة: {module}")
    except Exception as e:
        LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)

# --- معالج طلبات Webhook (تم التعديل هنا) ---
async def webhook_handler(request):
    # التحقق من الرمز السري لضمان أن الطلب قادم من تيليجرام
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return web.Response(status=403) # Forbidden
    
    try:
        # **(هنا التعديل الرئيسي)**
        # قراءة التحديث كـ JSON وتمريره مباشرة إلى الدالة الرسمية في Telethon
        update = await request.json()
        await client.handle_update(update)
        
    except Exception as e:
        LOGGER.error(f"!! فشل في معالجة تحديث Webhook: {e}", exc_info=True)
        # في حالة حدوث خطأ، نرد بخطأ داخلي في الخادم
        return web.Response(status=500)
    
    # نرد على تيليجرام بأننا استلمنا التحديث بنجاح
    return web.Response(status=200)

# --- معالج فحص الصحة (للتأكد من أن البوت يعمل) ---
async def health_check_handler(request):
    return web.Response(text="Bot is running via Webhook.")

# --- دالة التشغيل الرئيسية الجديدة (تم تعديلها وتحسينها) ---
async def main():
    try:
        # تهيئة قاعدة البيانات
        await init_db()
        LOGGER.info(">> اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        # **(تحسين)** تسجيل الدخول مع إيقاف جلب التحديثات التلقائي
        await client.start(bot_token=config.BOT_TOKEN, update_workers=0)
        me = await client.get_me()
        
        # الحصول على رابط النشر العام من Railway
        public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if not public_domain:
            # في حال عدم وجود الرابط، نحاول استخدام اسم الخدمة كبديل
            service_name = os.environ.get("RAILWAY_SERVICE_NAME")
            if service_name:
                 public_domain = f"{service_name}-production.up.railway.app"
                 LOGGER.warning(f"RAILWAY_PUBLIC_DOMAIN غير موجود، تم استخدام الرابط البديل: {public_domain}")
            else:
                LOGGER.critical("لم يتم العثور على RAILWAY_PUBLIC_DOMAIN أو RAILWAY_SERVICE_NAME.")
                sys.exit(1)
        
        # المسار الذي سيستمع إليه البوت، يمكن أن يكون أي شيء
        # لكن من الأفضل أن يكون سرياً مثل توكن البوت
        webhook_path = f"/{config.BOT_TOKEN}"
        webhook_url = f"https://{public_domain}{webhook_path}"

        # **(تحسين)** استخدام دالة Telethon المدمجة لإعداد الـ Webhook
        LOGGER.info(f">> يتم الآن إعداد رابط الويب هوك: {webhook_url} <<")
        await client.set_bot_webhook(url=webhook_url, secret_token=SECRET_TOKEN)
        LOGGER.info(">> تم إعداد رابط الويب هوك بنجاح. <<")
        
        # بدء المهمة الدورية للرسائل التلقائية
        asyncio.create_task(scheduler_task())
        
        # إعداد وتشغيل خادم الويب AIOHTTP
        app = web.Application()
        app.router.add_post(webhook_path, webhook_handler) # استخدام نفس المسار السري
        app.router.add_get("/", health_check_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        LOGGER.info(f">> البوت يعمل الآن بنظام Webhook على المنفذ {PORT}... <<")
        
        # إبقاء البرنامج يعمل إلى الأبد
        await client.run_until_disconnected()

    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    # استخدام client.loop.run_until_complete لضمان التوافق مع Telethon
    client.loop.run_until_complete(main())
