# plugins/cleaning.py

import asyncio
from telethon import events
from bot import client
from plugins.utils import get_user_rank, Ranks, db, save_db

@client.on(events.NewMessage(pattern=r"^مسح (\d+)$"))
async def delete_messages_by_count(event):
    """
    (جديد ومُحسَّن)
    Handler for .مسح <عدد>
    Deletes messages using the stored message history.
    """
    if not event.is_group:
        await event.reply("⚠️ هذا الأمر يعمل في المجموعات فقط.")
        return

    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        await event.reply("🚫 عذراً، هذا الأمر متاح لمشرفي المجموعة فما فوق.")
        return

    try:
        count_to_delete = int(event.pattern_match.group(1))
    except ValueError:
        return

    if not (1 <= count_to_delete <= 100):
        await event.reply("⚠️ العدد يجب أن يكون بين 1 و 100.")
        return

    chat_id_str = str(event.chat_id)
    
    # --- بداية المنطق الجديد: القراءة من الذاكرة ---
    message_history = db.get(chat_id_str, {}).get("message_history", [])
    
    if not message_history:
        await event.reply("ذاكرة الرسائل فارغة حالياً. يرجى الانتظار حتى يتم إرسال بعض الرسائل الجديدة.")
        return

    # استخراج أرقام الرسائل من السجل المحفوظ
    history_ids = [item["msg_id"] for item in message_history]

    # أخذ آخر عدد مطلوب من الرسائل المحفوظة
    ids_to_delete = history_ids[-(count_to_delete):]

    # إضافة رسالة الأمر نفسها إلى القائمة ليتم حذفها أيضاً
    ids_to_delete.append(event.message.id)
    # --- نهاية المنطق الجديد ---

    try:
        await client.delete_messages(event.chat_id, ids_to_delete)

        # حذف الرسائل المحذوفة من قاعدة البيانات للحفاظ على نظافتها
        # هذه خطوة مهمة جداً
        updated_history = [item for item in message_history if item["msg_id"] not in ids_to_delete]
        db[chat_id_str]["message_history"] = updated_history
        save_db(db)

        confirmation_msg = await event.respond(f"✅ **تم حذف {len(ids_to_delete)} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()

    except Exception as e:
        print(f"Error in cleaning module (by_count_from_db): {e}")
        await event.reply("⚠️ حدث خطأ أثناء محاولة الحذف. تأكد من صلاحياتي.")


@client.on(events.NewMessage(pattern=r"^مسح$"))
async def delete_messages_by_reply(event):
    """
    Handler for .مسح ( بالرد )
    This function remains as it is, simple and effective.
    """
    if not event.is_group:
        await event.reply("⚠️ هذا الأمر يعمل في المجموعات فقط.")
        return
    if not event.is_reply:
        await event.reply("⚠️ يرجى الرد على الرسالة التي تريد بدء الحذف منها.")
        return
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        await event.reply("🚫 عذراً، هذا الأمر متاح لمشرفي المجموعة فما فوق.")
        return
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
