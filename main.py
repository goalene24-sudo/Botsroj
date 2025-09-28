import logging
import importlib
import sys
from datetime import datetime
import asyncio
import os

# --- استيراد المكتبات اللازمة للويب ---
from aiohttp import web

# --- استيراد مكونات البوت ---
from bot import client
from plugins import ALL_MODULES
import config

# --- استيراد مكونات قاعدة البيانات ---
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import database
from database import init_db

# --- استيراد المهمة الدورية ---
from plugins.auto_messages import scheduler_task


# --- الإعدادات الأساسية ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


# --- معالجات طلبات الويب (Handlers) ---
async def handle_health_check(request):
    """يرد على فحص الصحة من Koyeb/Railway"""
    return web.Response(text="Bot is healthy and running!", status=200)

async def handle_webhook(request):
    """يستقبل تحديثات تليجرام ويعالجها"""
    try:
        # نقوم بتمرير بيانات التحديث مباشرة إلى مكتبة تيليثون
        await client.process_update(await request.json())
        return web.Response(status=200)
    except Exception as e:
        LOGGER.error(f"!! خطأ في معالجة تحديث Webhook: {e}", exc_info=True)
        return web.Response(status=500)

# --- دالة بدء التشغيل الرئيسية ---
async def main():
    """
    الدالة الرئيسية التي تقوم بتهيئة كل شيء وتشغيل البوت.
    """
    LOGGER.info("="*50)
    LOGGER.info(">>> بدء تشغيل بوت سروج بنظام Webhook... <<<")
    LOGGER.info("="*50)

    # --- الخطوة 1: تهيئة قاعدة البيانات ---
    LOGGER.info(">> [1/5] يتم الآن تهيئة محرك قاعدة البيانات... <<")
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        LOGGER.info(">> تم العثور على قاعدة بيانات PostgreSQL. جاري الاتصال... <<")
        engine = create_async_engine(db_url, echo=False)
    else:
        LOGGER.info(">> لم يتم العثور على قاعدة بيانات خارجية. سيتم استخدام ملف SQLite المحلي. <<")
        DB_NAME = "surooj.db"
        DB_URI = f"sqlite+aiosqlite:///{DB_NAME}?check_same_thread=False"
        engine = create_async_engine(DB_URI, echo=False, poolclass=NullPool)
    
    database.AsyncDBSession = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )
    await init_db(engine)
    LOGGER.info(">> [1/5] اكتملت تهيئة قاعدة البيانات بنجاح. <<")

    # --- الخطوة 2: تحميل الإضافات ---
    LOGGER.info(">> [2/5] يتم الآن تحميل كل الوحدات... <<")
    for module in ALL_MODULES:
        try:
            importlib.import_module(module)
            LOGGER.info(f"  - تم تحميل الوحدة: {module}")
        except Exception as e:
            LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)
    LOGGER.info(">> [2/5] اكتمل تحميل جميع الوحدات. <<")

    # --- الخطوة 3: تسجيل الدخول إلى تليجرام ---
    # لا نستخدم client.start() بالطريقة العادية، بل نسجل الدخول فقط
    await client.connect()
    if not await client.is_user_authorized():
        await client.sign_in(bot_token=config.BOT_TOKEN)
    me = await client.get_me()
    LOGGER.info(f">> [3/5] تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
    
    # --- الخطوة 4: إنشاء خادم الويب ---
    app = web.Application()
    app.router.add_get('/', handle_health_check) # لفحص الصحة
    app.router.add_post(f'/{config.BOT_TOKEN}', handle_webhook) # لاستقبال رسائل تليجرام
    
    runner = web.AppRunner(app)
    await runner.setup()
    PORT = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    LOGGER.info(f">> [4/5] خادم الويب يستمع الآن على البورت {PORT}... <<")

    # --- الخطوة 5: تسجيل عنوان الويب هوك لدى تليجرام ---
    # Koyeb/Railway يوفرانه في متغيرات البيئة
    # ملاحظة: RAILWAY_STATIC_URL قديم، Koyeb يستخدم KOYEB_PUBLIC_URL
    public_url_base = os.environ.get("KOYEB_PUBLIC_URL") or os.environ.get("RAILWAY_STATIC_URL")
    if not public_url_base:
        LOGGER.critical("!! لم يتم العثور على عنوان URL عام في متغيرات البيئة! لا يمكن تسجيل الويبهوك.")
        return

    webhook_url = f"https://{public_url_base}/{config.BOT_TOKEN}"
    await client.set_webhook(webhook_url)
    LOGGER.info(f">> [5/5] تم تسجيل Webhook على العنوان: {webhook_url.split('/')[-2]}/... <<")
    
    # --- بدء المهمة الدورية ---
    LOGGER.info(">> يتم الآن بدء مهمة الرسائل الدورية (الجدولة)... <<")
    asyncio.create_task(scheduler_task())
    
    LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر عبر Webhook! <<")

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    # هذا الجزء سيقوم بتشغيل دالة البدء الرئيسية
    # وسيبقي البوت يعمل بفضل خادم الويب
    try:
        asyncio.run(main())
        # إبقاء البرنامج يعمل للأبد
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info(">> تم إيقاف البوت. <<")
