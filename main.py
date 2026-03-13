import os
import asyncio
import logging
from telethon import TelegramClient
from quart import Quart
from database import init_db
from plugins import load_plugins
import config

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# إعداد تطبيق الويب (لفحص الصحة)
app = Quart(__name__)

@app.route('/')
async def health_check():
    return "Suruj Bot is Running Correctly!", 200

# إعداد بوت Telethon
client = TelegramClient('session_name', config.API_ID, config.API_HASH)

async def start_bot():
    """تشغيل البوت وتحميل الإضافات"""
    # تهيئة قاعدة البيانات
    init_db()
    
    # بدء تشغيل البوت
    await client.start(bot_token=config.BOT_TOKEN)
    logger.info("🚀 بوت سُرُوج (Telethon) بدأ العمل بنجاح!")
    
    # تحميل الإضافات
    load_plugins(client)
    
    # البقاء في وضع الاستماع
    await client.run_until_disconnected()

async def main():
    """تشغيل خادم الويب والبوت معاً في نفس الحلقة"""
    PORT = int(os.environ.get("PORT", 8000))
    
    # تشغيل المهمتين معاً لضمان السرعة القصوى
    await asyncio.gather(
        start_bot(),
        app.run_task(host='0.0.0.0', port=PORT)
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
