# plugins/sudo_panel.py

import asyncio
import os
import sys
from datetime import datetime
from telethon import events, Button
from bot import client, StartTime
import config
from .utils import db, get_uptime_string, save_db

# --- الدالة الرئيسية لبناء أزرار لوحة التحكم ---
def build_sudo_panel():
    buttons = [
        [Button.inline("📊 الإحصائيات العامة", data="sudo_panel:stats")],
        [Button.inline("📢 قسم الإذاعة", data="sudo_panel:broadcast")],
        # --- (تمت الإضافة) الأزرار الجديدة ---
        [Button.inline("🚫 الحظر العام", data="sudo_panel:gban"), Button.inline("🧑‍✈️ الترقيات العامة", data="sudo_panel:gadmin")],
        [Button.inline("🔄 إعادة التشغيل", data="sudo_panel:restart"), Button.inline("🛑 إيقاف التشغيل", data="sudo_panel:shutdown")],
        [Button.inline("📁 تحميل قاعدة البيانات", data="sudo_panel:get_db")],
    ]
    return buttons

# --- نص الرسالة الرئيسية للوحة التحكم ---
SUDO_PANEL_TEXT = "**⚙️ | لوحة تحكم المطور**\n\n**أهلاً بك يا مطوري. اختر أحد الأقسام للتحكم بالبوت:**"

# --- معالج الأمر الرئيسي لفتح اللوحة ---
@client.on(events.NewMessage(pattern="^/لوحه$"))
async def open_sudo_panel(event):
    # التأكد من أن الأمر في الخاص ومن المطور فقط
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return
    
    await event.reply(SUDO_PANEL_TEXT, buttons=build_sudo_panel())


# --- معالج ضغطات الأزرار في لوحة التحكم ---
@client.on(events.CallbackQuery(pattern=b"^sudo_panel:"))
async def sudo_panel_callback(event):
    # التأكد من أن المستخدم هو المطور
    if event.sender_id not in config.SUDO_USERS:
        return await event.answer("🚫 | هذه اللوحة مخصصة للمطور فقط.", alert=True)

    action = event.data.decode().split(':')[1]

    if action == "main":
        await event.edit(SUDO_PANEL_TEXT, buttons=build_sudo_panel())

    elif action == "restart":
        await event.edit("**🔄 | جاري إعادة تشغيل البوت...**")
        os.execl(sys.executable, sys.executable, "-m", "main")

    elif action == "shutdown":
        await event.edit("**🛑 | جاري إيقاف تشغيل البوت... إلى اللقاء.**")
        await client.disconnect()

    elif action == "stats":
        uptime = get_uptime_string(StartTime)
        group_count = len(db)
        unique_users = set()
        for chat_data in db.values():
            if "users" in chat_data:
                unique_users.update(chat_data["users"].keys())
        user_count = len(unique_users)
        stats_text = f"""**📊 | الإحصائيات العامة للبوت**

**- مدة التشغيل (Uptime):**
  `{uptime}`

**- عدد المجموعات المفعلة:**
  `{group_count}` **مجموعة**

**- عدد المستخدمين المسجلين:**
  `{user_count}` **مستخدم**
"""
        await event.edit(stats_text, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
    
    elif action == "broadcast":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**📢 | أرسل الآن رسالة الإذاعة التي تريد إرسالها لجميع المجموعات...**\n\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if response.text.strip().lower() == "الغاء":
                    return await conv.send_message("**☑️ | تم إلغاء الإذاعة.**")
                
                broadcast_message = response.message
                await conv.send_message("**⏳ | سأبدأ الآن ببث الرسالة...**")
                successful, failed = 0, 0
                all_chats = list(db.keys())
                for chat_id_str in all_chats:
                    try:
                        await client.send_message(int(chat_id_str), broadcast_message)
                        successful += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Broadcast failed for chat {chat_id_str}: {e}")
                        failed += 1
                await conv.send_message(f"**📡 | اكتملت الإذاعة!**\n**- ✅ نجح:** `{successful}`\n**- ❌ فشل:** `{failed}`")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "get_db":
        await event.answer("📁 | جاري تحضير الملف...")
        try:
            await client.send_file(event.chat_id, "database.json", caption="**🗄️ | النسخة الاحتياطية من `database.json`**")
        except Exception as e:
            await event.reply(f"**حدث خطأ:**\n`{e}`")

    # --- (جديد) معالج الحظر العام ---
    elif action == "gban":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🚫 | أرسل الآن ID المستخدم الذي تريد حظره عاماً...**\n\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if response.text.strip().lower() == "الغاء":
                    return await conv.send_message("**☑️ | تم إلغاء الأمر.**")
                
                try:
                    user_id_to_ban = int(response.text.strip())
                except ValueError:
                    return await conv.send_message("**⚠️ | ID غير صالح. يرجى إرسال أرقام فقط.**")

                await conv.send_message(f"**⏳ | سأقوم الآن بحظر `{user_id_to_ban}` من كل المجموعات...**")
                
                if "globally_banned" not in db: db["globally_banned"] = []
                if user_id_to_ban not in db["globally_banned"]:
                    db["globally_banned"].append(user_id_to_ban)
                    save_db(db)

                successful, failed = 0, 0
                all_chats = list(db.keys())
                for chat_id_str in all_chats:
                    try:
                        # نتأكد من أن المفتاح هو لمجموعة (رقم سالب)
                        if chat_id_str.startswith('-'):
                            await client.edit_permissions(int(chat_id_str), user_id_to_ban, view_messages=False)
                            successful += 1
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"GBan failed for chat {chat_id_str}: {e}")
                        failed += 1
                
                await conv.send_message(f"**🚫 | اكتمل الحظر العام!**\n**- ✅ تم الحظر في:** `{successful}` **مجموعة**\n**- ❌ فشل في:** `{failed}` **مجموعة**")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()
        
    # --- (جديد) معالج الترقيات العامة ---
    elif action == "gadmin":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🧑‍✈️ | أرسل الآن ID المستخدم الذي تريد ترقيته 'أدمن بوت' في كل المجموعات...**\n\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if response.text.strip().lower() == "الغاء":
                    return await conv.send_message("**☑️ | تم إلغاء الأمر.**")

                try:
                    user_id_to_promote = int(response.text.strip())
                except ValueError:
                    return await conv.send_message("**⚠️ | ID غير صالح. يرجى إرسال أرقام فقط.**")
                
                await conv.send_message(f"**⏳ | سأقوم الآن بترقية `{user_id_to_promote}` في كل المجموعات...**")
                
                promoted_in = 0
                all_chats = list(db.keys())
                for chat_id_str in all_chats:
                    # نتأكد من أن المفتاح هو لمجموعة
                    if chat_id_str.startswith('-'):
                        db[chat_id_str].setdefault("bot_admins", [])
                        if user_id_to_promote not in db[chat_id_str]["bot_admins"]:
                            db[chat_id_str]["bot_admins"].append(user_id_to_promote)
                            promoted_in += 1
                
                save_db(db)
                await conv.send_message(f"**🧑‍✈️ | اكتملت الترقية العامة!**\n**- ✅ تم ترقية المستخدم في:** `{promoted_in}` **مجموعة جديدة.**")

        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()
