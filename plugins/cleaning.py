# plugins/cleaning.py

import asyncio
from telethon import events
from bot import client
from plugins.utils import get_user_rank, Ranks
import traceback
# استدعاء دالة منخفضة المستوى للتجربة
from telethon.tl.functions.channels import DeleteMessagesRequest

@client.on(events.NewMessage(pattern=r"^مسح (\d+)$"))
async def delete_messages_by_count(event):
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

    try:
        ids_to_delete = []
        # لا زلنا نحتاج لقراءة السجل، وهو مكان حدوث الخطأ
        async for message in client.iter_messages(
            event.chat_id,
            limit=count_to_delete,
            offset_id=event.message.id
        ):
            ids_to_delete.append(message.id)
        ids_to_delete.append(event.message.id)
        
        if not ids_to_delete:
            return

        # --- محاولة استخدام دالة حذف مختلفة ---
        await client(DeleteMessagesRequest(
            channel=await event.get_input_chat(),
            id=ids_to_delete
        ))
        # ------------------------------------

        confirmation_msg = await event.respond(f"✅ **تم حذف {len(ids_to_delete)} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()

    except Exception as e:
        traceback.print_exc()
        error_name = type(e).__name__
        error_description = str(e)
        await event.reply(
            f"**❗ تم العثور على خطأ فني ❗**\n\n"
            f"**نوع الخطأ:**\n`{error_name}`\n\n"
            f"**الوصف التقني:**\n`{error_description}`"
        )


@client.on(events.NewMessage(pattern=r"^مسح$"))
async def delete_messages_by_reply(event):
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
        
        await client(DeleteMessagesRequest(
            channel=await event.get_input_chat(),
            id=message_ids_to_delete
        ))

        confirmation_msg = await event.respond(f"✅ **تم حذف {count} رسالة بنجاح.**")
        await asyncio.sleep(5)
        await confirmation_msg.delete()
    except Exception as e:
        print(f"Error in cleaning module (by_reply): {e}")
        await event.reply("⚠️ حدث خطأ. تأكد من أنني أمتلك صلاحية حذف الرسائل في هذه المجموعة.")
