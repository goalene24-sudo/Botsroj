import logging
import importlib
import sys
from telethon import TelegramClient
import config # نحن نستخدم ملف الإعدادات الصحيح الخاص بك

# --- الإعدادات الأساسية ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# --- تهيئة العميل (Client) ---
# هذا الكود مأخوذ من test.py الذي نجح 100%
try:
    client = TelegramClient(None, config.API_ID, config.API_HASH)
except Exception as e:
    LOGGER.critical(f"!! خطأ فادح عند تهيئة العميل: {e}", exc_info=True)
    sys.exit(1)

# --- قائمة الإضافات (Plugins) ---
# ابدأ بقائمة فارغة أو بإضافة واحدة فقط للاختبار
ALL_MODULES = [
    "plugins.core", # كمثال، ابدأ بهذه الإضافة فقط
    "plugins.utils",
    "plugins.admin",
    "plugins.events"
    "plugins.callbacks"
    # ... وهكذا
]

# --- تحميل الإضافات ---
LOGGER.info(">> يتم الآن تحميل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        LOGGER.info(f"  - تم تحميل الوحدة: {module}")
    except Exception as e:
        LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)


# --- دالة التشغيل الرئيسية ---
async def main():
    try:
        await client.start(bot_token=config.BOT_TOKEN)
        me = await client.get_me()
        LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
        LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
        await client.run_until_disconnected()
    except Exception as e:
        LOGGER.critical(f"!! فشل فادح أثناء تشغيل البوت: {e}", exc_info=True)

# --- بدء تشغيل البوت ---
if __name__ == "__main__":
    client.loop.run_until_complete(main())
