import logging
import sys
import importlib

# --- خطوة تشخيصية: إعداد اللوجر في البداية مباشرة ---
# هذا سيضمن تسجيل أي خطأ يحدث أثناء الاستيراد
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO,
    stream=sys.stdout  # تأكيد إخراج السجلات إلى المكان الصحيح
)

LOGGER = logging.getLogger(__name__)
LOGGER.info(">> [تشخيص] بدأ تشغيل ملف main.py.")

# --- خطوة تشخيصية: التحقق من كل استيراد على حدة ---
try:
    import config
    LOGGER.info(">> [تشخيص] نجح استيراد: config.py")
except Exception:
    LOGGER.critical("!! فشل فادح عند استيراد config.py", exc_info=True)
    sys.exit(1)

try:
    from bot import client
    LOGGER.info(">> [تشخيص] نجح استيراد: bot.py")
except Exception:
    LOGGER.critical("!! فشل فادح عند استيراد bot.py", exc_info=True)
    sys.exit(1)

try:
    from plugins import ALL_MODULES
    LOGGER.info(">> [تشخيص] نجح استيراد: plugins/__init__.py")
except Exception:
    LOGGER.critical("!! فشل فادح عند استيراد plugins/__init__.py", exc_info=True)
    sys.exit(1)


# --- الكود الأصلي للبوت ---
LOGGER.info(">> جميع عمليات الاستيراد الأساسية نجحت. يتم الآن تحميل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        LOGGER.info(f"  - تم تحميل الوحدة: {module}")
    except Exception:
        LOGGER.error(f"!! فشل تحميل الوحدة {module}", exc_info=True)

async def main_startup():
    await client.start(bot_token=config.BOT_TOKEN)
    me = await client.get_me()
    LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
    LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main_startup())
