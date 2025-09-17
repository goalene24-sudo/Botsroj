# plugins/tagging.py
from telethon import events
from telethon.tl.types import ChannelParticipantsAdmins
from bot import client
from .utils import check_activation, is_admin

@client.on(events.NewMessage(pattern=r"^(مشرفين|تبليغ|@admin)$"))
async def report_admins(event):
    """Tags all human admins in a group."""
    if event.is_private or not await check_activation(event.chat_id):
        return

    # رسالة الانتظار
    zed = await event.reply("`جاري إرسال نداء للمشرفين...`")
    
    mentions = "**🚨 نداء للمشرفين الكرام 🗣️**\n"
    admin_count = 0
    
    try:
        async for user in client.iter_participants(event.chat_id, filter=ChannelParticipantsAdmins):
            if not user.bot and not user.deleted:
                admin_count += 1
                mentions += f"[\u2063](tg://user?id={user.id})"
        
        if admin_count > 0:
            # إذا كان المستخدم يرد على رسالة، يتم إرسال التقرير كرد عليها
            reply_to = await event.get_reply_message()
            await client.send_message(event.chat_id, mentions, reply_to=reply_to)
        else:
            await zed.edit("**لا يوجد مشرفون في هذه المجموعة.**")
            return
            
    except Exception as e:
        await zed.edit(f"**حدث خطأ:**\n`{e}`")
        return

    await zed.delete()
    # لا تحذف رسالة الأمر الأصلية في حال كانت @admin ليراها المشرفون
    if event.raw_text.lower() != "@admin":
        await event.delete()


@client.on(events.NewMessage(pattern=r"^منشن(?:\s|$)(.*)"))
async def custom_mention(event):
    """Creates a custom mention for a user."""
    if event.is_private or not await check_activation(event.chat_id):
        return
        
    # يتطلب أن يكون المستخدم مشرفًا لاستخدام الأمر
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("🚫 | **عذراً، هذا الأمر مخصص للمشرفين فقط.**")
        return

    text_to_show = event.pattern_match.group(1)
    reply = await event.get_reply_message()

    if not reply:
        await event.reply("**يجب استخدام هذا الأمر بالرد على رسالة الشخص الذي تريد عمل منشن له.**")
        return

    if not text_to_show:
        await event.reply("**يجب أن تكتب النص الذي تريده أن يظهر في المنشن بعد كلمة `منشن`.**\n\n**مثال:** `منشن الفائز بالمسابقة` (بالرد على رسالة الفائز).")
        return
        
    user = await reply.get_sender()
    
    try:
        mention_html = f"<a href='tg://user?id={user.id}'>{text_to_show}</a>"
        await client.send_message(event.chat_id, mention_html, parse_mode='html', reply_to=reply)
        await event.delete()
    except Exception as e:
        await event.reply(f"**حدث خطأ:**\n`{e}`")