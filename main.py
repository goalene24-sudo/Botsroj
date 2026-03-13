import os
import asyncio
import logging
import threading
import http.server
import socketserver
from telethon import TelegramClient
# استيراد ملفات البوت الأصلية (تأكد من مطابقة الأسماء لمشروعك)
from database import init_db
from plugins import load_plugins
import config

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- خادم فحص الصحة (Health Check) المدمج ---
# هذا الخادم لا يحتاج مكتبة Quart ولا يسبب أي بطء
def run_health_server():
    PORT = int(os.environ.get("PORT", 8000))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        logger.info(f"✅ Health Check Server Running on Port {PORT}")
        httpd.serve_forever()

async def start_bot():
    """تشغيل بوت سُرُوج الأصلي (Telethon)"""
    
    # 1. تهيئة قاعدة البيانات
    try:
        init_db()
        logger.info("✅ تم تهيئة قاعدة البيانات.")
    except Exception as e:
        logger.error(f"❌ خطأ في قاعدة البيانات: {e}")

    # 2. إعداد وتشغيل Telethon
    client = TelegramClient('suruj_session', config.API_ID, config.API_HASH)
    
    await client.start(bot_token=config.BOT_TOKEN)
    logger.info("🚀 بوت سُرُوج (Telethon) بدأ العمل الآن!")

    # 3. تحميل الإضافات
    try:
        load_plugins(client)
        logger.info("✅ تم تحميل الإضافات.")
    except Exception as e:
        logger.error(f"❌ خطأ أثناء تحميل الإضافات: {e}")
    
    # 4. البقاء في وضع الاستماع
    await client.run_until_disconnected()

if __name__ == '__main__':
    # تشغيل خادم الصحة في الخلفية
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # تشغيل البوت في الحلقة الرئيسية
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
