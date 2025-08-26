from telethon import TelegramClient
from datetime import datetime
import config
import logging

StartTime = datetime.now()

try:
    # --- هذا هو السطر الذي تم تصحيحه ---
    # لقد استبدلنا None باسم جلسة وليكن 'saruj_bot'
    client = TelegramClient('saruj_bot', config.API_ID, config.API_HASH)
    # ------------------------------------
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    logging.critical(f"!! خطأ فادح عند تهيئة البوت: {e}", exc_info=True)
    exit(1)
