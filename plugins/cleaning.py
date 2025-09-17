# plugins/cleaning.py

import asyncio
from telethon import events
from bot import client
# --- (تم التعديل) استيراد المكونات الجديدة ---
from plugins.utils import get_user_rank, Ranks
from sqlalchemy.future import select
from sqlalchemy import delete
from database import AsyncDBSession
from models import MessageHistory

# --- دالة مساعدة مركزية لتجنب تكرار الكود ---
async def purge_messages_by_type(event, target_types, count_to_delete, command_text):
    """
    دالة عامة لحذف الرسائل بناءً على نوعها من السجل المحفوظ في قاعدة البيانات.
    """
    ids_to_delete = []
    try:
        async with AsyncDBSession() as session:
            # 1. فلترة السجل للعثور على الرسائل من النوع المطلوب
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

            # 2. إضافة رسالة الأمر نفسها للحذف
            ids_to_delete.append(event.message.id)

            # 3. الحذف من تيليجرام
            await client.delete_messages(event.chat_id, ids_to_delete)

            # 4. تنظيف قاعدة البيانات من الرسائل المحذوفة
            delete_stmt = delete(MessageHistory).where(MessageHistory.msg_id.in_(ids_to_delete))
            await session.execute(delete_stmt)
            await session.commit()
            
            # رسالة تأكيد مخصصة
            deleted_count = len(ids_to_delete)
            reply_text = f"✅ **تم حذف {deleted_count - 1} {command_text} بنجاح.**" if count_to_delete < 100 else f"✅ **تم حذف كل الـ {command_text} ({deleted_count - 1}) المحفوظة بنجاح.**"
            confirmation_msg = await event.respond(reply_text)
            await asyncio.sleep(5)
            await confirmation_msg.delete()

    except Exception as e:
        print(f"Error in specialized purge: {e}")
        # إذا فشل الحذف من تيليجرام، لا تقم بالحذف من قاعدة البيانات
        await event.reply("⚠️ حدث خطأ أثناء محاولة الحذف. تأكد من صلاحياتي.")


# --- (مُصحَّح) الأوامر المتخصصة مع عدد اختياري ---

@client.on(events.NewMessage(pattern=r"^(مسح الصور|مسح صور)(?: (\d+))?$"))
async def purge_photos(event):
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["photo"], count, "صورة")

@client.on(events.NewMessage(pattern=r"^(مسح الميديا)(?: (\d+))?$"))
async def purge_media(event):
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    media_types = ["photo", "video", "sticker", "gif"]
    await purge_messages_by_type(event, media_types, count, "ميديا")

@client.on(events.NewMessage(pattern=r"^(مسح الكلايش|مسح كلايش)(?: (\d+))?$"))
async def purge_long_texts(event):
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["long_text"], count, "كليشة")

@client.on(events.NewMessage(pattern=r"^(مسح الروابط|مسح روابط)(?: (\d+))?$"))
async def purge_links(event):
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["url"], count, "رابط")

@client.on(events.NewMessage(pattern=r"^(مسح التوجيه|مسح توجيه)(?: (\d+))?$"))
async def purge_forwards(event):
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["forward"], count, "رسالة موجهة")

# --- (مُصحَّح) الأوامر الأساسية ---

@client.on(events.NewMessage(pattern=r"^مسح (\d+)$"))
async def delete_messages_by_count(event):
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    count = int(event.pattern_match.group(1))
    all_types = ["text", "photo", "video", "sticker", "gif", "url", "forward", "long_text"]
    await purge_messages_by_type(event, all_types, count, "رسالة")

@client.on(events.NewMessage(pattern=r"^مسح$"))
async def delete_messages_by_reply(event):
    if not event.is_group: return
    if not event.is_reply:
        await event.reply("⚠️ يرجى الرد على الرسالة التي تريد بدء الحذف منها.")
        return
    user_rank = await get_user_rank(event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD: return
    try:
        start_msg_id = event.message.reply_to_msg_id
        end_msg_id = event.message.id
        message_ids_to_delete = [i for i in range(start_msg_id, end_msg_id + 1)]
        count = len(message_ids_to_delete)
        
        await client.delete_messages(event.chat_id, message_ids_to_delete)

        confirmation_msg = await event.respond(f"✅ **تم حذف {count} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()
    except Exception as e:
        print(f"Error in cleaning module (by_reply): {e}")
        await event.reply("⚠️ حدث خطأ. تأكد من أنني أمتلك صلاحية حذف الرسائل في هذه المجموعة.")
