import os
import asyncio
import threading
import http.server
import socketserver
import logging

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. تشغيل خادم الصحة فوراً (لضمان بقاء Koyeb سعيداً)
def run_health_server():
    PORT = int(os.environ.get("PORT", 8000))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_health_server, daemon=True).start()

# 2. استيراد المكونات (بعد تشغيل الخادم)
from bot import client 
from plugins import load_plugins

async def start_suruj():
    # تحميل الإضافات أولاً لضمان ربط المستمعات (Events) قبل الاتصال
    logger.info("⏳ يتم الآن تحميل الإضافات...")
    load_plugins(client)
    
    # الآن نبدأ البوت
    logger.info("📡 جاري الاتصال بتلجرام...")
    await client.start()
    await client.send_message('me', '✅ أنا اشتغلت يا عبودي!')

    me = await client.get_me()
    logger.info(f"🚀 بوت سُرُوج (@{me.username}) يعمل الآن وبأقصى سرعة!")
    
    # البقاء في وضع الاستماع
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(start_suruj())
    except Exception as e:
        logger.error(f"❌ حدث خطأ غير متوقع: {e}")
