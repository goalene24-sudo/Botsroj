import logging
from telethon import events
from telethon.tl.types import MessageEntityUrl

from bot import client
from database import AsyncDBSession
from models import MessageHistory

# استيراد دالة التحقق من التفعيل
from .utils import check_activation

logger = logging.getLogger(__name__)

def get_message_type(event):
    """تحدد نوع الرسالة لتحزينها في قاعدة البيانات."""
    if event.photo: return "photo"
    if event.video or event.video_note: return "video"
    if event.sticker: return "sticker"
    if event.gif: return "gif"
    if event.fwd_from: return "forward"
    if event.entities:
        for entity in event.entities:
            if isinstance(entity, MessageEntityUrl):
                return "url"
    if event.document: return "document"
    if event.audio: return "audio"
    if event.voice: return "voice"
    if event.text and len(event.text) > 200:
        return "long_text"
    if event.text: return "text"
    return "unknown"

@client.on(events.NewMessage(func=lambda e: e.is_private == False))
async def message_history_logger(event):
    """
    هذا المعالج يستمع لكل الرسائل الجديدة في المجموعات
    ويقوم بتسجيلها في قاعدة البيانات لميزة التحليلات والمسح.
    """
    if not await check_activation(event.chat_id):
        return

    try:
        if await event.get_sender() and (await event.get_sender()).bot:
            return
    except Exception:
        return

    try:
        # --- (تم التعديل هنا) ---
        # تحديد نوع الرسالة قبل تسجيلها
        msg_type = get_message_type(event)
        
        # إنشاء سجل جديد للرسالة مع النوع
        new_log = MessageHistory(
            chat_id=event.chat_id,
            user_id=event.sender_id,
            msg_id=event.id,
            message_text=event.text,
            msg_type=msg_type
        )

        async with AsyncDBSession() as session:
            session.add(new_log)
            await session.commit()

    except Exception as e:
        logger.error(f"Failed to log message to history for chat {event.chat_id}: {e}")
