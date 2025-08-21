# bot.py
from telethon import TelegramClient
from datetime import datetime
import config

# -- (جديد) تسجيل وقت بدء التشغيل --
StartTime = datetime.now()

try:
    client = TelegramClient('bot_session', config.API_ID, config.API_HASH)
except Exception as e:
    print(f"!! خطأ فادح عند تهيئة البوت: {e}"); 
    exit(1)
