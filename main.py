import logging
import importlib
import sys
import os
import asyncio
import secrets
from aiohttp import web
import aiohttp # <-- التأكد من استيراد المكتبة للطلبات اليدوية

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
PORT = int(os.environ.get("PORT", 8080))
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

# --- معالج طلبات Webhook ---
async def webhook_handler(request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return web.Response(status=403)
    
    try:
        update = await request.json()
        await client.handle_update(update)
        
    except Exception as e:
        LOGGER.error(f"!! فشل في معالجة تحديث Webhook: {e}", exc_info=True)
        return web.Response(status=500)
    
    return web.Response(status=200)

# --- معالج فحص الصحة ---
async def health_check_handler(request):
    return web.Response(text="Bot is running via Webhook.")

# --- دالة التشغيل الرئيسية ---
async def main():
    try:
        await init_db()
        LOGGER.info(">> اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        
        public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if not public_domain:
            service_name = os.environ.get("RAILWAY_SERVICE_NAME")
            if service_name:
                 public_domain = f"{service_name}-production.up.railway.app"
                 LOGGER.warning(f"RAILWAY_PUBLIC_DOMAIN غير موجود، تم استخدام الرابط البديل: {public_domain}")
            else:
                LOGGER.critical("لم يتم العثور على RAILWAY_PUBLIC_DOMAIN أو RAILWAY_SERVICE_NAME.")
                sys.exit(1)
        
        # المسار يجب أن يكون فريداً لمنع الوصول غير المصرح به
        webhook_path = f"/{config.BOT_TOKEN}"
        webhook_url = f"https://{public_domain}{webhook_path}"

        # **(تم التعديل هنا)**
        # العودة إلى طريقة إعداد الويب هوك اليدوية باستخدام aiohttp
        LOGGER.info(f">> يتم الآن إعداد Webhook عبر طلب مباشر إلى تيليجرام... <<")
        api_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setWebhook"
        params = {'url': webhook_url, 'secret_token': SECRET_TOKEN}
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, data=params) as response:
                result = await response.json()
                if result.get("ok"):
                    LOGGER.info(f">> تم إعداد Webhook بنجاح: {result.get('description')} <<")
                else:
                    LOGGER.error(f"!! فشل فادح في إعداد Webhook: {result.get('description')}")
                    sys.exit(1)
        
        asyncio.create_task(scheduler_task())
        
        app = web.Application()
        app.router.add_post(webhook_path, webhook_handler)
        app.router.add_get("/", health_check_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        LOGGER.info(f">> البوت يعمل الآن بنظام Webhook على المنفذ {PORT}... <<")
        
        await client.run_until_disconnected()

    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    client.loop.run_until_complete(main())
