import logging
import importlib
import sys
import os
import asyncio
import secrets
from aiohttp import web
import aiohttp # <-- إضافة للتأكد من وجودها

# استيراد الأدوات اللازمة من تيليثون لمعالجة التحديثات
from telethon.tl import types, functions

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
PORT = int(os.environ.get("PORT", 8000))
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
        data = await request.read()
        await client._updates_processor.process_update(
            await client._updates_processor.reader.read_update(data), None
        )
    except Exception as e:
        LOGGER.error(f"!! فشل في معالجة تحديث Webhook: {e}", exc_info=True)
    return web.Response(status=200)

# --- معالج فحص الصحة ---
async def health_check_handler(request):
    return web.Response(text="Bot is running via Webhook.")

# --- دالة التشغيل الرئيسية الجديدة ---
async def main():
    try:
        # تهيئة قاعدة البيانات
        await init_db()
        LOGGER.info(">> اكتملت تهيئة قاعدة البيانات بنجاح. <<")

        # تسجيل الدخول إلى تيليجرام
        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        
        # الحصول على رابط النشر العام من Railway
        public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if not public_domain:
            LOGGER.critical("لم يتم العثور على RAILWAY_PUBLIC_DOMAIN. تأكد من أن خدمتك لديها رابط عام.")
            sys.exit(1)
        webhook_url = f"https://{public_domain}/webhook"

        # --- (تم التعديل هنا) إعداد Webhook عبر طلب HTTP مباشر ---
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
                    sys.exit(1) # إيقاف البوت إذا فشل إعداد Webhook
        
        # بدء المهمة الدورية
        asyncio.create_task(scheduler_task())
        
        # إعداد وتشغيل خادم الويب AIOHTTP
        app = web.Application()
        app.router.add_post("/webhook", webhook_handler)
        app.router.add_get("/", health_check_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        LOGGER.info(f">> البوت يعمل الآن بنظام Webhook على المنفذ {PORT}... <<")
        
        await asyncio.Event().wait()

    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)
        sys.exit(1)
    finally:
        LOGGER.info(">> يتم الآن إيقاف تشغيل البوت... <<")
        await client.disconnect()

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    asyncio.run(main())
