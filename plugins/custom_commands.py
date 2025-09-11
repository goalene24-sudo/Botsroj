import json
from telethon import events
from bot import client

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from database import DBSession
from models import User, GlobalSetting

async def get_global_setting(key, default=None):
    """جلب قيمة إعداد عام من قاعدة البيانات."""
    async with DBSession() as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting and setting.value:
            try:
                # محاولة فك تشفير JSON، إذا فشل، أرجع القيمة كنص عادي
                return json.loads(setting.value)
            except (json.JSONDecodeError, TypeError):
                return setting.value
        return default

@client.on(events.NewMessage(pattern=r"^[!/](.*)"))
async def custom_command_handler(event):
    if event.is_private:
        return

    # استخراج اسم الأمر بدون بادئة
    command = event.pattern_match.group(1).lower().strip().split()[0]
    
    # البحث عن الأمر في قاعدة البيانات
    custom_commands = await get_global_setting("custom_commands", {})
    
    if command in custom_commands:
        command_data = custom_commands[command]
        reply_template = command_data.get("reply")
        
        if reply_template:
            # --- جلب البيانات الديناميكية ---
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # جلب بيانات المستخدم من قاعدة البيانات الجديدة
            async with DBSession() as session:
                result = await session.execute(
                    select(User).where(User.chat_id == chat.id, User.user_id == sender.id)
                )
                user_data = result.scalar_one_or_none()
            
            msg_count = user_data.msg_count if user_data else 0
            points = user_data.points if user_data else 0
            
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
