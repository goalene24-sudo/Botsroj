# plugins/custom_commands.py

from telethon import events
from bot import client
from .utils import db

@client.on(events.NewMessage(pattern=r"^[!/](.*)"))
async def custom_command_handler(event):
    if event.is_private:
        return

    # استخراج اسم الأمر بدون بادئة
    command = event.pattern_match.group(1).lower().strip().split()[0]
    
    # البحث عن الأمر في قاعدة البيانات
    custom_commands = db.get("custom_commands", {})
    
    if command in custom_commands:
        reply_template = custom_commands[command].get("reply")
        
        if reply_template:
            # --- جلب البيانات الديناميكية ---
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            chat_id_str = str(chat.id)
            sender_id_str = str(sender.id)
            user_data = db.get(chat_id_str, {}).get("users", {}).get(sender_id_str, {})
            
            msg_count = user_data.get("msg_count", 0)
            points = user_data.get("points", 0)
            
            # --- استبدال المتغيرات بالبيانات الحقيقية ---
            try:
                # التأكد من أن القالب هو نص
                if not isinstance(reply_template, str):
                    reply_template = str(reply_template)

                final_reply = reply_template.format(
                    user_first_name=sender.first_name,
                    user_mention=f"[{sender.first_name}](tg://user?id={sender.id})",
                    user_id=sender.id,
                    points=points,
                    msg_count=msg_count,
                    chat_title=chat.title
                )
                await event.reply(final_reply, parse_mode='md')
            except KeyError as e:
                # هذا يحدث إذا كتب المطور متغيراً خاطئاً
                await event.reply(f"**⚠️ خطأ في الأمر المخصص!**\nالمتغير `{e}` غير معروف. يرجى مراجعته من لوحة المطور.")
            except Exception as e:
                await event.reply(f"**⚠️ حدث خطأ غير متوقع أثناء تنفيذ الأمر المخصص:**\n`{e}`")

        # أوقف المعالجة هنا لمنع تضارب الأوامر مع الأوامر الأساسية
        raise events.StopPropagation