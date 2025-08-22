from telethon import TelegramClient
from datetime import datetime
import config
import logging

StartTime = datetime.now()

try:
    client = TelegramClient(None, config.API_ID, config.API_HASH)
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    logging.critical(f"!! خطأ فادح عند تهيئة البوت: {e}", exc_info=True)
    exit(1)
    
