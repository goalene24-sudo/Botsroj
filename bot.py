from telethon import TelegramClient
from datetime import datetime
import config

# -- تسجيل وقت بدء التشغيل --
StartTime = datetime.now()

try:
    # استخدام "None" بدلاً من اسم الجلسة يجبر البوت على استخدام الذاكرة
    # وهذا هو الأسلوب الصحيح للبوتات على الاستضافات
    client = TelegramClient(None, config.API_ID, config.API_HASH)
except Exception as e:
    # استخدام اللوجر أفضل من print
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.critical(f"!! خطأ فادح عند تهيئة البوت: {e}", exc_info=True)
    exit(1)
