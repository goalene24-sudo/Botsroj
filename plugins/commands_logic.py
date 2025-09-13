import logging
import re
from sqlalchemy.future import select

from .utils import has_bot_permission
from database import AsyncDBSession
from models import Chat

logger = logging.getLogger(__name__)

# قاموس أنواع الأقفال
LOCK_TYPES_MAP = {
    "الصور": "photo", "الفيديو": "video", "المتحركه": "gif", "الملصقات": "sticker",
    "الروابط": "url", "المعرف": "username", "التوجيه": "forward", "الملفات": "document",
    "الاغاني": "audio", "الصوت": "voice", "السيلفي": "video_note",
    "الكلايش": "long_text", "الدردشه": "text", "الانلاين": "inline", "البوتات": "bot",
    "الجهات": "contact", "الموقع": "location", "الفشار": "game",
    "الانكليزيه": "english", "التعديل": "edit",
}

async def get_or_create_chat(session, chat_id):
    """الحصول على مجموعة من قاعدة البيانات أو إنشائها إذا لم تكن موجودة."""
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(id=chat_id, settings={}, lock_settings={})
        session.add(chat)
    return chat

# (تم التعديل) الوظيفة الآن تستقبل النص المترجم مباشرة
async def lock_unlock_logic(event, command_text):
    """منطق معالجة أوامر القفل والفتح."""
    try:
        if not await has_bot_permission(event):
            return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")

        # استخدام النص المترجم الذي تم تمريره مباشرة
        match = re.match(r"^(قفل|فتح) (.+)$", command_text)
        if not match:
            return 

        action = match.group(1)
        target = match.group(2).strip()
        
        lock_key = LOCK_TYPES_MAP.get(target)
        
        if not lock_key:
            return await event.reply(f"**⚠️ | الأمر `{target}` غير معروف.**")

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            if chat.lock_settings is None:
                chat.lock_settings = {}
            
            new_lock_settings = chat.lock_settings.copy()
            current_state_is_locked = new_lock_settings.get(lock_key, False)

            if action == "قفل":
                if current_state_is_locked:
                    return await event.reply(f"**🔒 | {target} مقفلة بالفعل، لا تقلق عزيزي.**")
                new_lock_settings[lock_key] = True
                await event.reply(f"**✅ | تم قفل {target} بنجاح.**")
            else: # فتح
                if not current_state_is_locked:
                    return await event.reply(f"**🔓 | {target} مفتوحة بالفعل.**")
                new_lock_settings[lock_key] = False
                await event.reply(f"**✅ | تم فتح {target} بنجاح.**")
            
            chat.lock_settings = new_lock_settings
            await session.commit()
            
    except Exception as e:
        logger.error(f"استثناء في lock_unlock_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")
