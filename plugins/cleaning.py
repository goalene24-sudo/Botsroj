import asyncio
import logging
from datetime import datetime, timedelta
from telethon import events
from telethon.tl.types import MessageEntityUrl

from bot import client
from .utils import get_user_rank, Ranks, check_activation
from sqlalchemy.future import select
from sqlalchemy import delete
from database import AsyncDBSession
from models import MessageHistory

logger = logging.getLogger(__name__)

# --- تم حذف دالة get_message_type والمعالج message_recorder_handler من هنا ---
# --- لأنه تم نقل وظيفتهما إلى ملف message_logger.py الجديد ---


# --- دالة المسح المركزية والمحسنة ---
async def purge_messages_by_type(event, target_types, count_to_delete, command_text):
    ids_to_delete = []
    try:
        async with AsyncDBSession() as session:
            stmt = (
                select(MessageHistory.msg_id)
                .where(MessageHistory.chat_id == event.chat_id, MessageHistory.msg_type.in_(target_types))
                .order_by(MessageHistory.id.desc())
                .limit(count_to_delete)
            )
            result = await session.execute(stmt)
            ids_to_delete = result.scalars().all()

            if not ids_to_delete:
                await event.reply(f"لم أجد أي رسائل من نوع '{command_text}' في ذاكرة البوت.")
                return

            ids_to_delete.append(event.message.id)
            
            # الحذف من تيليجرام
            await client.delete_messages(event.chat_id, ids_to_delete)

            # تنظيف قاعدة البيانات
            delete_stmt = delete(MessageHistory).where(MessageHistory.msg_id.in_(ids_to_delete))
            await session.execute(delete_stmt)
            await session.commit()
            
            deleted_count = len(ids_to_delete)
            reply_text = f"✅ **تم حذف {deleted_count - 1} {command_text} بنجاح.**"
            confirmation_msg = await event.respond(reply_text)
            await asyncio.sleep(5)
            await confirmation_msg.delete()

    except Exception as e:
        logger.error(f"Error in specialized purge for {command_text}: {e}")
        await event.reply("⚠️ حدث خطأ أثناء محاولة الحذف. تأكد من صلاحياتي.")

# --- الأوامر المتخصصة ---

@client.on(events.NewMessage(pattern=r"^(مسح الصور|مسح صور)(?: (\d+))?$"))
async def purge_photos(event):
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["photo"], count, "صورة")

@client.on(events.NewMessage(pattern=r"^(مسح الميديا)(?: (\d+))?$"))
async def purge_media(event):
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    media_types = ["photo", "video", "sticker", "gif"]
    await purge_messages_by_type(event, media_types, count, "ميديا")

@client.on(events.NewMessage(pattern=r"^(مسح الكلايش|مسح كلايش)(?: (\d+))?$"))
async def purge_long_texts(event):
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["long_text"], count, "كليشة")

@client.on(events.NewMessage(pattern=r"^(مسح الروابط|مسح روابط)(?: (\d+))?$"))
async def purge_links(event):
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["url"], count, "رابط")

@client.on(events.NewMessage(pattern=r"^(مسح التوجيه|مسح توجيه)(?: (\d+))?$"))
async def purge_forwards(event):
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["forward"], count, "رسالة موجهة")

# --- الأوامر الأساسية ---

@client.on(events.NewMessage(pattern=r"^مسح (\d+)$"))
async def delete_messages_by_count(event):
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(1))
    all_types = ["text", "photo", "video", "sticker", "gif", "url", "forward", "long_text"]
    await purge_messages_by_type(event, all_types, count, "رسالة")

@client.on(events.NewMessage(pattern=r"^مسح$"))
async def delete_messages_by_reply(event):
    if not event.is_group: return
    if not event.is_reply:
        return await event.reply("⚠️ يرجى الرد على الرسالة التي تريد بدء الحذف منها.")
    
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return

    try:
        start_msg_id = event.message.reply_to_msg_id
        end_msg_id = event.message.id
        message_ids_to_delete = list(range(start_msg_id, end_msg_id + 1))
        count = len(message_ids_to_delete)
        
        # تقسيم الحذف إلى مجموعات صغيرة لتجنب أخطاء تيليجرام
        for i in range(0, count, 100):
            chunk = message_ids_to_delete[i:i + 100]
            await client.delete_messages(event.chat_id, chunk)
            await asyncio.sleep(1) # استراحة قصيرة بين الطلبات

        confirmation_msg = await event.respond(f"✅ **تم حذف {count} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()
    except Exception as e:
        logger.error(f"Error in cleaning module (by_reply): {e}")
        await event.reply("⚠️ حدث خطأ. تأكد من أنني أمتلك صلاحية حذف الرسائل في هذه المجموعة.")
