# plugins/cleaning.py

import asyncio
from telethon import events
from bot import client
from plugins.utils import get_user_rank, RANK_ADMIN

@client.on(events.NewMessage(pattern=r"^مسح (\d+)$"))
async def delete_messages_by_count(event):
    """
    Handler for .مسح <عدد>
    Deletes a specified number of recent messages.
    """
    if not event.is_group:
        await event.reply("⚠️ هذا الأمر يعمل في المجموعات فقط.")
        return

    # --- فحص الصلاحيات ---
    user_rank = await get_user_rank(event.chat_id, event.sender_id)
    if user_rank < RANK_ADMIN:
        await event.reply("🚫 عذراً، هذا الأمر متاح للأدمنية فما فوق.")
        return

    try:
        count_to_delete = int(event.pattern_match.group(1))
    except ValueError:
        return

    if not (1 <= count_to_delete <= 100):
        await event.reply("⚠️ العدد يجب أن يكون بين 1 و 100.")
        return

    try:
        # جمع أرقام الرسائل المراد حذفها
        # سيتم حذف رسالة الأمر + العدد المحدد من الرسائل التي تسبقها
        messages_to_delete = []
        async for msg in client.iter_messages(event.chat_id, limit=count_to_delete, max_id=event.message.id):
            messages_to_delete.append(msg.id)

        # إضافة رسالة الأمر نفسها إلى القائمة إذا لم تكن موجودة
        if event.message.id not in messages_to_delete:
            messages_to_delete.append(event.message.id)

        await client.delete_messages(event.chat_id, messages_to_delete)

        # إرسال رسالة تأكيد وحذفها بعد 5 ثوانٍ
        confirmation_msg = await event.respond(f"✅ **تم حذف {count_to_delete} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()

    except Exception as e:
        # في حال حدوث خطأ (مثل عدم وجود صلاحية الحذف لدى البوت)
        print(f"Error in cleaning module (by_count): {e}")
        await event.reply("⚠️ حدث خطأ. تأكد من أنني أمتلك صلاحية حذف الرسائل في هذه المجموعة.")


@client.on(events.NewMessage(pattern=r"^مسح$"))
async def delete_messages_by_reply(event):
    """
    Handler for .مسح ( بالرد )
    Deletes all messages from the replied-to message up to the command message.
    """
    if not event.is_group:
        await event.reply("⚠️ هذا الأمر يعمل في المجموعات فقط.")
        return

    if not event.is_reply:
        await event.reply("⚠️ يرجى الرد على الرسالة التي تريد بدء الحذف منها.")
        return

    # --- فحص الصلاحيات ---
    user_rank = await get_user_rank(event.chat_id, event.sender_id)
    if user_rank < RANK_ADMIN:
        await event.reply("🚫 عذراً، هذا الأمر متاح للأدمنية فما فوق.")
        return

    try:
        start_msg_id = event.message.reply_to_msg_id
        end_msg_id = event.message.id

        # جمع كل أرقام الرسائل بين رسالة البداية والنهاية
        message_ids_to_delete = [i for i in range(start_msg_id, end_msg_id + 1)]
        
        count = len(message_ids_to_delete)
        await client.delete_messages(event.chat_id, message_ids_to_delete)

        # إرسال رسالة تأكيد وحذفها بعد 5 ثوانٍ
        confirmation_msg = await event.respond(f"✅ **تم حذف {count} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()

    except Exception as e:
        print(f"Error in cleaning module (by_reply): {e}")
        await event.reply("⚠️ حدث خطأ. تأكد من أنني أمتلك صلاحية حذف الرسائل في هذه المجموعة.")
