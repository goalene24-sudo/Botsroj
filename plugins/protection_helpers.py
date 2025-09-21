import logging
import re
from datetime import datetime, timedelta

from telethon import Button
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
from .utils import has_bot_permission, get_user_rank, Ranks, get_or_create_user
from database import AsyncDBSession
from models import Chat, User, BotAdmin, Creator, Vip

logger = logging.getLogger(__name__)

# --- المتغيرات المشتركة ---

LOCK_TYPES_MAP = {
    "الصور": "photo", "الفيديو": "video", "المتحركه": "gif", "الملصقات": "sticker",
    "الروابط": "url", "المعرف": "username", "التوجيه": "forward", "الملفات": "document",
    "الاغاني": "audio", "الصوت": "voice", "السيلفي": "video_note",
    "الكلايش": "long_text", "الدردشه": "text", "الانلاين": "inline", "البوتات": "bot",
    "الجهات": "contact", "الموقع": "location", "الفشار": "game",
    "الانكليزيه": "english", "التعديل": "edit",
    "التكرار": "flood",
}

# --- الدوال المساعدة المشتركة ---

async def get_or_create_chat(session, chat_id):
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(id=chat_id, settings={}, lock_settings={})
        session.add(chat)
    return chat

async def set_chat_setting(chat_id, key, value):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        if chat.settings is None: chat.settings = {}
        new_settings = chat.settings.copy()
        new_settings[key] = value
        chat.settings = new_settings
        flag_modified(chat, "settings")
        await session.commit()