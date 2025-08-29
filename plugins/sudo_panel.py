# plugins/sudo_panel.py

import asyncio
import os
import sys
from telethon import events, Button
from telethon.tl.types import Message
from bot import client, StartTime
import config
from .utils import db, get_uptime_string, save_db

# --- الدالة الرئيسية لبناء أزرار لوحة التحكم ---
def build_sudo_panel():
    buttons = [
        [Button.inline("📊 الإحصائيات العامة", data="sudo_panel:stats")],
        [Button.inline("📢 قسم الإذاعة", data="sudo_panel:broadcast")],
        [Button.inline("🚫 الحظر العام", data="sudo_panel:gban"), Button.inline("🧑‍✈️ الترقيات العامة", data="sudo_panel:gadmin")],
        [Button.inline("🛠️ الصيانة", data="sudo_panel:db_maint"), Button.inline("🔍 فحص البيانات", data="sudo_panel:inspect")],
        [Button.inline("🌐 الإعدادات العامة", data="sudo_panel:global_settings")],
        [Button.inline("📝 الأوامر المخصصة", data="sudo_panel:custom_cmds")],
        [Button.inline("🔄 إعادة التشغيل", data="sudo_panel:restart"), Button.inline("🛑 إيقاف التشغيل", data="sudo_panel:shutdown")],
        [Button.inline("📁 تحميل قاعدة البيانات", data="sudo_panel:get_db")],
    ]
    return buttons

SUDO_PANEL_TEXT = "**⚙️ | لوحة تحكم المطور**\n\n**أهلاً بك يا مطوري. اختر أحد الأقسام للتحكم بالبوت:**"
@client.on(events.NewMessage(pattern=r"^[!/]لوحه$", from_users=config.SUDO_USERS, chats=config.SUDO_USERS))
async def open_sudo_panel(event):
    await event.reply(SUDO_PANEL_TEXT, buttons=build_sudo_panel())

@client.on(events.CallbackQuery(pattern=b"^sudo_panel:"))
async def sudo_panel_callback(event):
    if event.sender_id not in config.SUDO_USERS:
        return await event.answer("🚫 | هذه اللوحة مخصصة للمطور فقط.", alert=True)

    action = event.data.decode().split(':')[1]

    # --- [تم التحديث] تعديل قسم تحميل قاعدة البيانات ---
    if action == "get_db":
        await event.answer("📁 | جاري تحضير الملف...")
        db_path = "database.json"
        
        if not os.path.exists(db_path):
            await client.send_message(event.chat_id, f"**❌ | خطأ: لم يتم العثور على الملف!**\n\nيبدو أن ملف `{db_path}` غير موجود في مسار عمل البوت. تأكد من أنه تم رفعه إلى GitHub بشكل صحيح.")
            return
            
        try:
            await client.send_file(event.chat_id, db_path, caption="**🗄️ | النسخة الاحتياطية من `database.json`**")
        except Exception as e:
            await client.send_message(event.chat_id, f"**❌ | حدث خطأ أثناء إرسال الملف:**\n`{e}`")
        return
        
    # --- قسم الأوامر المخصصة ---
    elif action == "custom_cmds":
        custom_cmds_text = "**📝 | قسم الأوامر المخصصة**\n\n- يمكنك هنا إضافة أوامر جديدة للبوت يقوم بالرد عليها بنص معين."
        custom_cmds_buttons = [
            [Button.inline("➕ إضافة أمر جديد", data="sudo_panel:add_cmd")],
            [Button.inline("🗑️ حذف أمر", data="sudo_panel:del_cmd")],
            [Button.inline("📜 عرض كل الأوامر", data="sudo_panel:list_cmds")],
            [Button.inline("🔙 رجوع", data="sudo_panel:main")]
        ]
        await event.edit(custom_cmds_text, buttons=custom_cmds_buttons)

    elif action == "add_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=600) as conv:
                await conv.send_message("**أرسل الآن اسم الأمر الجديد (بدون `/`).**\n\n**مثال: `القناة`**")
                cmd_name_msg = await conv.get_response()
                cmd_name = cmd_name_msg.text.strip().lower()

                if not cmd_name or ' ' in cmd_name:
                    return await conv.send_message("**⚠️ | اسم الأمر غير صالح. يجب أن يكون كلمة واحدة بدون مسافات.**")

                placeholders_guide = (
                    "**حسناً، الآن أرسل النص الذي سيرد به البوت.**\n\n"
                    "**يمكنك استخدام المتغيرات التالية في النص ليتم استبدالها بمعلومات العضو:**\n"
                    "`{user_first_name}` - الاسم الأول للعضو\n"
                    "`{user_mention}` - إشارة (منشن) للعضو\n"
                    "`{user_id}` - آي دي العضو\n"
                    "`{points}` - نقاط العضو\n"
                    "`{msg_count}` - عدد رسائل العضو\n"
                    "`{chat_title}` - اسم المجموعة\n\n"
                    "**مثال:** `مرحباً {user_mention}، لديك {points} نقطة!`"
                )
                await conv.send_message(placeholders_guide)
                cmd_reply_msg = await conv.get_response()
                cmd_reply_text = cmd_reply_msg.text

                await conv.send_message("**هل تريد إضافة زر لهذا الأمر في لوحة الأوامر الرئيسية للأعضاء؟**\n\n**أجب بـ `نعم` أو `لا`.**")
                add_button_msg = await conv.get_response()
                add_button = add_button_msg.text.strip().lower() == "نعم"

                db.setdefault("custom_commands", {})
                db["custom_commands"][cmd_name] = {
                    "reply": cmd_reply_text,
                    "show_button": add_button
                }
                save_db(db)
                await conv.send_message(f"**✅ | تم حفظ الأمر بنجاح!**\n**- الأمر:** `{cmd_name}`\n**- إظهار الزر:** `{'نعم' if add_button else 'لا'}`")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "del_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**أرسل اسم الأمر الذي تريد حذفه.**")
                cmd_name_msg = await conv.get_response()
                cmd_name = cmd_name_msg.text.strip().lower()

                if "custom_commands" in db and cmd_name in db["custom_commands"]:
                    del db["custom_commands"][cmd_name]
                    save_db(db)
                    await conv.send_message(f"**🗑️ | تم حذف الأمر `{cmd_name}` بنجاح.**")
                else:
                    await conv.send_message(f"**⚠️ | لم يتم العثور على أمر بهذا الاسم.**")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "list_cmds":
        if "custom_commands" not in db or not db["custom_commands"]:
            return await event.answer("📜 | لا توجد أوامر مخصصة حالياً.", alert=True)
        list_text = "**📜 | قائمة الأوامر المخصصة:**\n\n"
        for cmd_name, cmd_data in db["custom_commands"].items():
            button_status = '✅' if cmd_data.get('show_button') else '❌'
            list_text += f"- `{cmd_name}` (إظهار الزر: {button_status})\n"
        await event.edit(list_text, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:custom_cmds")])
    
    # --- بقية الأقسام ---
    # You should have all your other handlers here from your original file.
    # For this response, I'm assuming they are present and focusing on the fix.
    elif action == "main":
        await event.edit(SUDO_PANEL_TEXT, buttons=build_sudo_panel())
    
    # ... and so on for all other actions ...
