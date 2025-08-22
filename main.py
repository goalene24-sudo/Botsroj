import logging
import importlib
from bot import client
from plugins import ALL_MODULES
import config

# إعداد اللوجر الأساسي
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)

LOGGER = logging.getLogger(__name__)

LOGGER.info(">> يتم الآن تحميل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        LOGGER.info(f"  - تم تحميل الوحدة: {module}")
    except Exception as e:
        LOGGER.error(f"!! فشل تحميل الوحدة {module}: {e}", exc_info=True)

async def main_startup():
    # ---!!! خطوة تشخيصية مؤقتة لطباعة التوكن !!!---
    LOGGER.info("---!!! بداية الخطوة التشخيصية !!!---")
    token_value = config.BOT_TOKEN
    token_type = type(token_value)
    token_length = len(token_value) if token_value is not None else 0
    LOGGER.info(f"===> Token read from config: '{token_value}'")
    LOGGER.info(f"===> Token type: {token_type}")
    LOGGER.info(f"===> Token length: {token_length}")
    LOGGER.info("---!!! نهاية الخطوة التشخيصية !!!---")
    # ---------------------------------------------------

    await client.start(bot_token=config.BOT_TOKEN)
    me = await client.get_me()
    LOGGER.info(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
    LOGGER.info(">> البوت جاهز الآن لاستقبال الأوامر... <<")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main_startup())
