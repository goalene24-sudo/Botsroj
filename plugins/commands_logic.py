import logging
import re
from sqlalchemy.future import select

from .utils import has_bot_permission, get_user_rank, Ranks
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, Vip

logger = logging.getLogger(__name__)

# ... (The existing lock/unlock logic will be here) ...

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
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(id=chat_id, settings={}, lock_settings={})
        session.add(chat)
    return chat

async def lock_unlock_logic(event, command_text):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")

        match = re.match(r"^(قفل|فتح) (.+)$", command_text)
        if not match: return 

        action = match.group(1)
        target = match.group(2).strip()
        
        lock_key = LOCK_TYPES_MAP.get(target)
        if not lock_key:
            return await event.reply(f"**⚠️ | الأمر `{target}` غير معروف.**")

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            if chat.lock_settings is None: chat.lock_settings = {}
            
            new_lock_settings = chat.lock_settings.copy()
            current_state_is_locked = new_lock_settings.get(lock_key, False)

            if action == "قفل":
                if current_state_is_locked: return await event.reply(f"**🔒 | {target} مقفلة بالفعل.**")
                new_lock_settings[lock_key] = True
                await event.reply(f"**✅ | تم قفل {target} بنجاح.**")
            else:
                if not current_state_is_locked: return await event.reply(f"**🔓 | {target} مفتوحة بالفعل.**")
                new_lock_settings[lock_key] = False
                await event.reply(f"**✅ | تم فتح {target} بنجاح.**")
            
            chat.lock_settings = new_lock_settings
            await session.commit()
            
    except Exception as e:
        logger.error(f"استثناء في lock_unlock_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")


# --- (تمت الإضافة) منطق الأوامر الإدارية ---

async def kick_logic(event):
    """منطق أمر الطرد."""
    try:
        if not await has_bot_permission(event):
            return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")

        reply = await event.get_reply_message()
        if not reply:
            return await event.reply("**⚠️ | يجب استخدام هذا الأمر بالرد على رسالة شخص لطرده.**")

        user_to_kick = await reply.get_sender()
        actor = await event.get_sender()
        
        me = await event.client.get_me()
        if user_to_kick.id == me.id:
            return await event.reply("**تريدني اطرد نفسي شدتحس بله😒**")
        if user_to_kick.id == actor.id:
            return await event.reply("**لا يمكنك طرد نفسك!**")

        actor_rank = await get_user_rank(actor.id, event.chat_id)
        target_rank = await get_user_rank(user_to_kick.id, event.chat_id)

        if target_rank >= actor_rank:
            return await event.reply("**❌ | لا يمكنك طرد شخص يمتلك رتبة مساوية لك أو أعلى.**")

        await event.client.kick_participant(event.chat_id, user_to_kick.id)
        await event.reply(f"**✅ | تم طرد العضو [{user_to_kick.first_name}](tg://user?id={user_to_kick.id}) من المجموعة بنجاح.**")
    except Exception as e:
        logger.error(f"استثناء في kick_logic: {e}", exc_info=True)
        await event.reply(f"**حدث خطأ:**\n`{e}`")


async def set_rank_logic(event, command_text):
    """منطق أوامر رفع وتنزيل الرتب."""
    try:
        # استخلاص الرتبة من الأمر
        rank_map = {
            "رفع ادمن": (Ranks.CREATOR, BotAdmin, "ادمن في البوت"),
            "تنزيل ادمن": (Ranks.CREATOR, BotAdmin, "ادمن في البوت"),
            "رفع منشئ": (Ranks.OWNER, Creator, "منشئ في البوت"),
            "تنزيل منشئ": (Ranks.OWNER, Creator, "منشئ في البوت"),
            "رفع مميز": (Ranks.ADMIN, Vip, "عضو مميز"),
            "تنزيل مميز": (Ranks.ADMIN, Vip, "عضو مميز"),
        }
        
        action = "رفع" if command_text.startswith("رفع") else "تنزيل"
        required_rank, db_model, rank_name = rank_map[command_text]

        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < required_rank:
            return await event.reply("**🚫 | رتبتك لا تسمح لك باستخدام هذا الأمر.**")

        reply = await event.get_reply_message()
        if not reply: return await event.reply("**⚠️ | يجب استخدام هذا الأمر بالرد على شخص.**")
        
        user_to_manage = await reply.get_sender()
        if user_to_manage.bot: return await event.reply("**لا يمكنك تعديل رتب البوتات.**")

        target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
        if target_rank >= actor_rank:
            return await event.reply("**❌ | لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

        async with AsyncDBSession() as session:
            result = await session.execute(select(db_model).where(
                db_model.chat_id == event.chat_id, 
                db_model.user_id == user_to_manage.id
            ))
            is_rank_holder = result.scalar_one_or_none()

            if action == "رفع":
                if is_rank_holder: return await event.reply(f"**ℹ️ | هذا الشخص بالفعل {rank_name}.**")
                session.add(db_model(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**✅ | تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى {rank_name}.**")
            else: # تنزيل
                if not is_rank_holder: return await event.reply(f"**ℹ️ | هذا الشخص ليس {rank_name} أصلاً.**")
                await session.delete(is_rank_holder)
                await event.reply(f"**☑️ | تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من رتبة {rank_name}.**")
            
            await session.commit()

    except Exception as e:
        logger.error(f"استثناء في set_rank_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")
