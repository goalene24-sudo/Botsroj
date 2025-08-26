# plugins/cleaning.py

import asyncio
from telethon import events
from bot import client
from plugins.utils import get_user_rank, Ranks, db, save_db

# --- دالة مساعدة مركزية لتجنب تكرار الكود ---
async def purge_messages_by_type(event, target_types, count_to_delete, command_text):
    """
    دالة عامة لحذف الرسائل بناءً على نوعها من السجل المحفوظ.
    """
    chat_id_str = str(event.chat_id)
    message_history = db.get(chat_id_str, {}).get("message_history", [])
    
    if not message_history:
        await event.reply("ذاكرة الرسائل فارغة حالياً. يرجى الانتظار حتى يتم إرسال بعض الرسائل الجديدة.")
        return

    # 1. فلترة السجل للعثور على الرسائل من النوع المطلوب
    filtered_messages = [msg for msg in message_history if msg.get("type") in target_types]

    if not filtered_messages:
        await event.reply(f"لم أجد أي رسائل من هذا النوع في آخر {len(message_history)} رسالة.")
        return

    # 2. أخذ العدد المطلوب من الرسائل التي تم فلترتها
    ids_to_delete = [msg["msg_id"] for msg in filtered_messages]
    # إذا كان العدد المحدد أكبر من عدد الرسائل المتاحة، فسيتم حذف المتاح فقط
    ids_to_delete = ids_to_delete[-count_to_delete:]

    # 3. إضافة رسالة الأمر نفسها للحذف
    ids_to_delete.append(event.message.id)

    try:
        await client.delete_messages(event.chat_id, ids_to_delete)

        # 4. تنظيف قاعدة البيانات من الرسائل المحذوفة
        updated_history = [item for item in message_history if item["msg_id"] not in ids_to_delete]
        if chat_id_str in db:
            db[chat_id_str]["message_history"] = updated_history
            save_db(db)
        
        # رسالة تأكيد مخصصة
        deleted_count = len(ids_to_delete)
        reply_text = f"✅ **تم حذف {deleted_count - 1} {command_text} بنجاح.**" if count_to_delete < 100 else f"✅ **تم حذف كل الـ {command_text} ({deleted_count - 1}) المحفوظة بنجاح.**"
        confirmation_msg = await event.respond(reply_text)
        await asyncio.sleep(5)
        await confirmation_msg.delete()

    except Exception as e:
        print(f"Error in specialized purge: {e}")
        await event.reply("⚠️ حدث خطأ أثناء محاولة الحذف. تأكد من صلاحياتي.")

# --- (تم التحديث) الأوامر المتخصصة مع عدد اختياري ---

@client.on(events.NewMessage(pattern=r"^(مسح الصور|مسح صور)(?: (\d+))?$"))
async def purge_photos(event):
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["photo"], count, "صورة")

@client.on(events.NewMessage(pattern=r"^(مسح الميديا)(?: (\d+))?$"))
async def purge_media(event):
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    media_types = ["photo", "video", "sticker", "gif"]
    await purge_messages_by_type(event, media_types, count, "ميديا")

@client.on(events.NewMessage(pattern=r"^(مسح الكلايش|مسح كلايش)(?: (\d+))?$"))
async def purge_long_texts(event):
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["long_text"], count, "كليشة")

@client.on(events.NewMessage(pattern=r"^(مسح الروابط|مسح روابط)(?: (\d+))?$"))
async def purge_links(event):
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["url"], count, "رابط")

@client.on(events.NewMessage(pattern=r"^(مسح التوجيه|مسح توجيه)(?: (\d+))?$"))
async def purge_forwards(event):
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
    count = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 100
    await purge_messages_by_type(event, ["forward"], count, "رسالة موجهة")

# --- الأوامر الأساسية (تبقى كما هي) ---

@client.on(events.NewMessage(pattern=r"^مسح (\d+)$"))
async def delete_messages_by_count(event):
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
    count = int(event.pattern_match.group(1))
    all_types = ["text", "photo", "video", "sticker", "gif", "url", "forward", "long_text"]
    await purge_messages_by_type(event, all_types, count, "رسالة")

@client.on(events.NewMessage(pattern=r"^مسح$"))
async def delete_messages_by_reply(event):
    if not event.is_group: return
    if not event.is_reply:
        await event.reply("⚠️ يرجى الرد على الرسالة التي تريد بدء الحذف منها.")
        return
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN: return
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
