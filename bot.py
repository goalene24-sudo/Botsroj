from telethon import TelegramClient
from datetime import datetime
import config
import logging

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# وقت بدء تشغيل البوت
StartTime = datetime.now()

# هذا هو الجزء الوحيد الذي نحتاجه من هذا الملف
# تعريف العميل (client) حتى تتمكن بقية الملفات من استيراده
try:
    client = TelegramClient('saruj_bot', config.API_ID, config.API_HASH)
    logger.info("تم تهيئة العميل (client) بنجاح.")
except Exception as e:
    logger.critical(f"!! خطأ فادح عند تهيئة العميل: {e}", exc_info=True)
    exit(1)
