import logging
import importlib
from bot import client
from plugins import ALL_MODULES
import config

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# ---!!! خطوة تشخيصية: تم تعطيل تحميل الإضافات مؤقتاً !!!---
LOGGER.info(">> [تشخيص] تم تخطي تحميل الوحدات (plugins) لاختبار تسجيل الدخول الأساسي. <<")
# for module in ALL_MODULES:
#     try:
#         importlib.import_module(module)
#         LOGGER.info(f"  - تم تحميل الوحدة: {module}")
#     except Exception as e:
#         LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)
# -----------------------------------------------------------------

async def main_startup():
    await client.start(bot_token=config.BOT_TOKEN)
    me = await client.get_me()
    LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
    LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main_startup())
