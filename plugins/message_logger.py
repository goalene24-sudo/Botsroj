import logging
from telethon import events

from bot import client
from database import AsyncDBSession
from models import MessageHistory

# استيراد دالة التحقق من التفعيل
from .utils import check_activation

logger = logging.getLogger(__name__)

@client.on(events.NewMessage(func=lambda e: e.is_private == False))
async def message_history_logger(event):
    """
    هذا المعالج يستمع لكل الرسائل الجديدة في المجموعات
    ويقوم بتسجيلها في قاعدة البيانات لميزة التحليلات.
    """
    # لا تقم بتسجيل الرسائل من المجموعات غير المفعلة
    if not await check_activation(event.chat_id):
        return

    # لا تقم بتسجيل الرسائل من البوتات الأخرى
    try:
        if await event.get_sender() and (await event.get_sender()).bot:
            return
    except Exception:
        # تجاهل الأخطاء المحتملة في جلب المرسل (مثلاً في القنوات المجهولة)
        return

    try:
        # إنشاء سجل جديد للرسالة
        # يتم إضافة الوقت تلقائياً من قبل قاعدة البيانات
        new_log = MessageHistory(
            chat_id=event.chat_id,
            user_id=event.sender_id,
            msg_id=event.id,
            message_text=event.text # سيكون فارغاً للصور والملصقات، وهذا طبيعي
        )

        async with AsyncDBSession() as session:
            session.add(new_log)
            await session.commit()

    except Exception as e:
        # تسجيل أي خطأ يحدث بصمت دون إيقاف البوت
        logger.error(f"Failed to log message to history for chat {event.chat_id}: {e}")