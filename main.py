import logging
import importlib
from bot import client
from plugins import ALL_MODULES
import config

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)

print(">> يتم الآن تحميل الوحدات... <<")
for module in ALL_MODULES:
    try:
        importlib.import_module(module)
        print(f"  - تم تحميل الوحدة: {module}")
    except Exception as e:
        print(f"!! فشل تحميل الوحدة {module}: {e}")

async def main_startup():
    await client.start(bot_token=config.BOT_TOKEN)
    me = await client.get_me()
    print(f">> تم تسجيل الدخول بنجاح كـ {me.first_name} <<")
    print(">> البوت جاهز الآن لاستقبال الأوامر... <<")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        # تم تصحيح الخطأ الإملائي هنا
        client.loop.run_until_complete(main_startup())
        
