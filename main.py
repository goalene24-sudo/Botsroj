import os
import asyncio
import threading
import http.server
import socketserver
from bot import client  # استدعاء العميل كما هو بملفاتك الأصلية
from plugins import load_plugins # استدعاء المحرك كما هو
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# خادم الصحة (Health Check) لكي لا يغلق Koyeb البوت
def run_health_server():
    PORT = int(os.environ.get("PORT", 8000))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

async def start_suruj():
    # تشغيل العميل (Telethon)
    await client.start()
    logger.info("🚀 بوت سُرُوج بدأ العمل!")
    
    # تحميل الإضافات بنظامك الأصلي (بدون أي تعديل بالأسماء)
    load_plugins(client) 
    
    # البقاء في وضع الاستماع
    await client.run_until_disconnected()

if __name__ == '__main__':
    # تشغيل خادم الصحة في Thread معزول تماماً عن البوت
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # تشغيل الحلقة الرئيسية للبوت
    asyncio.run(start_suruj())
