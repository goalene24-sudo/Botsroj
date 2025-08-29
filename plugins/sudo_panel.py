# plugins/sudo_panel.py

import asyncio
import os
import sys
from telethon import events, Button
from telethon.errors.rpcerrorlist import UserNotParticipantError
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
        [Button.inline("🔄 إعادة التشغيل", data="sudo_panel:restart"), Button.inline("🛑 إيقاف التشغيل", data="sudo_panel:shutdown")],
        [Button.inline("📁 تحميل قاعدة البيانات", data="sudo_panel:get_db")],
    ]
    return buttons

# --- نص الرسالة الرئيسية للوحة التحكم ---
SUDO_PANEL_TEXT = "**⚙️ | لوحة تحكم المطور**\n\n**أهلاً بك يا مطوري. اختر أحد الأقسام للتحكم بالبوت:**"

# --- معالج الأمر الرئيسي لفتح اللوحة ---
@client.on(events.NewMessage(pattern=r"^[!/]لوحه$", from_users=config.SUDO_USERS, chats=config.SUDO_USERS))
async def open_sudo_panel(event):
    await event.reply(SUDO_PANEL_TEXT, buttons=build_sudo_panel())


# --- معالج ضغطات الأزرار في لوحة التحكم ---
@client.on(events.CallbackQuery(pattern=b"^sudo_panel:"))
async def sudo_panel_callback(event):
    if event.sender_id not in config.SUDO_USERS:
        return await event.answer("🚫 | هذه اللوحة مخصصة للمطور فقط.", alert=True)

    action = event.data.decode().split(':')[1]

    if action == "main":
        await event.edit(SUDO_PANEL_TEXT, buttons=build_sudo_panel())

    elif action == "restart":
        await event.edit("**🔄 | جاري إعادة تشغيل البوت...**")
        os.execl(sys.executable, sys.executable, "-m", "bot")

    elif action == "shutdown":
        await event.edit("**🛑 | جاري إيقاف تشغيل البوت... إلى اللقاء.**")
        await client.disconnect()

    elif action == "stats":
        uptime = get_uptime_string(StartTime)
        group_count = sum(1 for key in db.keys() if isinstance(key, int) and key < 0)
        
        # حساب المستخدمين الفريدين بدقة أكبر
        unique_users = set()
        for chat_id, chat_data in db.items():
            if isinstance(chat_data, dict) and "users" in chat_data:
                # التأكد من أن المفاتيح هي أرقام (معرفات مستخدمين)
                user_ids = [user_id for user_id in chat_data["users"].keys() if isinstance(user_id, int)]
                unique_users.update(user_ids)
        user_count = len(unique_users)

        stats_text = f"""**📊 | الإحصائيات العامة للبوت**

**- مدة التشغيل (Uptime):** `{uptime}`
**- عدد المجموعات المفعلة:** `{group_count}` مجموعة
**- عدد المستخدمين المسجلين:** `{user_count}` مستخدم
"""
        await event.edit(stats_text, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
    
    elif action == "broadcast":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**📢 | أرسل الآن رسالة الإذاعة...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if not response.text or response.text.strip().lower() == "الغاء": 
                    return await conv.send_message("**☑️ | تم إلغاء الإذاعة.**")
                
                await conv.send_message("**⏳ | سأبدأ الآن ببث الرسالة...**")
                successful, failed = 0, 0
                all_chats = [key for key in db.keys() if isinstance(key, int) and key < 0]
                for chat_id in all_chats:
                    try:
                        await client.send_message(chat_id, response.message)
                        successful += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Broadcast failed for chat {chat_id}: {e}")
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

    elif action == "gban":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🚫 | أرسل الآن ID المستخدم للحظر العام...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if not response.text or response.text.strip().lower() == "الغاء": 
                    return await conv.send_message("**☑️ | تم إلغاء الأمر.**")
                
                try: 
                    user_id_to_ban = int(response.text.strip())
                except ValueError: 
                    return await conv.send_message("**⚠️ | ID غير صالح.**")
                
                await conv.send_message(f"**⏳ | سأقوم الآن بحظر `{user_id_to_ban}`...**")
                db.setdefault("globally_banned", []).append(user_id_to_ban)
                save_db(db)

                successful, failed = 0, 0
                all_chats = [key for key in db.keys() if isinstance(key, int) and key < 0]
                for chat_id in all_chats:
                    try:
                        await client.edit_permissions(chat_id, user_id_to_ban, view_messages=False)
                        successful += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"GBan failed for chat {chat_id}: {e}")
                        failed += 1
                await conv.send_message(f"**🚫 | اكتمل الحظر العام!**\n**- ✅ تم الحظر في:** `{successful}`\n**- ❌ فشل في:** `{failed}`")
        except asyncio.TimeoutError: 
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()
        
    elif action == "gadmin":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🧑‍✈️ | أرسل الآن ID المستخدم للترقية العامة...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if not response.text or response.text.strip().lower() == "الغاء": 
                    return await conv.send_message("**☑️ | تم إلغاء الأمر.**")

                try: 
                    user_id_to_promote = int(response.text.strip())
                except ValueError: 
                    return await conv.send_message("**⚠️ | ID غير صالح.**")

                await conv.send_message(f"**⏳ | سأقوم الآن بترقية `{user_id_to_promote}`...**")
                promoted_in = 0
                all_chats = [key for key in db.keys() if isinstance(key, int) and key < 0]
                for chat_id in all_chats:
                    db.setdefault(chat_id, {}).setdefault("bot_admins", [])
                    if user_id_to_promote not in db[chat_id]["bot_admins"]:
                        db[chat_id]["bot_admins"].append(user_id_to_promote)
                        promoted_in += 1
                save_db(db)
                await conv.send_message(f"**🧑‍✈️ | اكتملت الترقية!**\n**- ✅ تمت الترقية في:** `{promoted_in}` **مجموعة.**")
        except asyncio.TimeoutError: 
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "db_maint":
        await event.edit("**🛠️ | جاري فحص قاعدة البيانات...**")
        inactive_chats = []
        all_chats = [key for key in db.keys() if isinstance(key, int) and key < 0]
        for chat_id in all_chats:
            try:
                await client.get_entity(chat_id)
                await asyncio.sleep(1)
            except Exception:
                inactive_chats.append(chat_id)
        
        if not inactive_chats:
            return await event.edit("**✅ | قاعدة البيانات نظيفة!**", buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
        
        for chat_id in inactive_chats:
            if chat_id in db: 
                del db[chat_id]
        save_db(db)
        await event.edit(f"**🗑️ | اكتملت الصيانة!**\n**تم تنظيف `{len(inactive_chats)}` مجموعة غير نشطة.**", buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])

    elif action == "inspect":
        inspect_text = "**🔍 | قسم فحص البيانات**\n\n**اختر نوع البيانات:**"
        inspect_buttons = [
            [Button.inline("فحص مجموعة 🏙️", data="sudo_panel:inspect_group"), Button.inline("فحص مستخدم 👤", data="sudo_panel:inspect_user")],
            [Button.inline("🔙 رجوع", data="sudo_panel:main")]
        ]
        await event.edit(inspect_text, buttons=inspect_buttons)

    elif action == "inspect_group":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🏙️ | أرسل الآن ID المجموعة...**")
                response = await conv.get_response()
                try:
                    chat_id = int(response.text.strip())
                except ValueError:
                    return await conv.send_message("**ID غير صالح.**")

                chat_data = db.get(chat_id)
                if not chat_data: 
                    return await conv.send_message("**لم يتم العثور على بيانات لهذه المجموعة.**")
                
                report = f"**📄 | تقرير المجموعة `{chat_id}`**\n"
                report += f"- أعضاء مسجلين: {len(chat_data.get('users', {}))}\n"
                report += f"- أدمنية البوت: {len(chat_data.get('bot_admins', []))}\n"
                await conv.send_message(report)
        except asyncio.TimeoutError: 
            await event.reply("**⏰ | انتهى الوقت.**")
            await event.answer()

    elif action == "inspect_user":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**👤 | أرسل الآن ID المستخدم...**")
                response = await conv.get_response()
                try:
                    user_id = int(response.text.strip())
                except ValueError:
                    return await conv.send_message("**ID غير صالح.**")

                report = f"**📄 | تقرير المستخدم `{user_id}`**\n"
                is_gbanned = user_id in db.get("globally_banned", [])
                report += f"- الحظر العام: {'محظور 🚫' if is_gbanned else 'غير محظور ✅'}\n"
                
                groups_found_in, total_msgs = [], 0
                for chat_id, chat_data in db.items():
                    if isinstance(chat_data, dict) and "users" in chat_data and user_id in chat_data["users"]:
                        groups_found_in.append(chat_id)
                        total_msgs += chat_data["users"][user_id].get("msg_count", 0)
                report += f"- مجموع الرسائل: {total_msgs}\n- موجود في: `{len(groups_found_in)}` مجموعة\n"
                await conv.send_message(report)
        except asyncio.TimeoutError: 
            await event.reply("**⏰ | انتهى الوقت.**")
            await event.answer()

    # --- (جديد) قسم الإعدادات العامة ---
    elif action == "global_settings":
        settings_text = "**🌐 | الإعدادات العامة للبوت**\n\n**اختر الإجراء الذي تريد القيام به:**"
        disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
        settings_buttons = [
            [Button.inline("🚫 تعطيل أمر عام", data="sudo_panel:g_disable_cmd"), Button.inline("✅ تفعيل أمر عام", data="sudo_panel:g_enable_cmd")],
            [Button.inline(f"📜 عرض الأوامر المعطلة ({len(disabled_cmds)})", data="sudo_panel:g_list_disabled")],
            [Button.inline("🔙 رجوع", data="sudo_panel:main")]
        ]
        await event.edit(settings_text, buttons=settings_buttons)

    elif action == "g_disable_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🚫 | أرسل الآن اسم الأمر الذي تريد تعطيله على مستوى البوت بالكامل (بدون `/` أو `!`).**\n\n**مثال: `ايدي`**")
                response = await conv.get_response()
                if not response.text: return
                cmd_to_disable = response.text.strip().lower().replace("/", "").replace("!", "")
                
                db.setdefault("global_settings", {}).setdefault("disabled_cmds", [])
                if cmd_to_disable in db["global_settings"]["disabled_cmds"]:
                    return await conv.send_message(f"**⚠️ | الأمر `{cmd_to_disable}` معطل بالفعل.**")
                
                db["global_settings"]["disabled_cmds"].append(cmd_to_disable)
                save_db(db)
                await conv.send_message(f"**✅ | تم تعطيل الأمر `{cmd_to_disable}` في جميع المجموعات.**")
        except asyncio.TimeoutError: 
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "g_enable_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**✅ | أرسل الآن اسم الأمر الذي تريد إعادة تفعيله...**")
                response = await conv.get_response()
                if not response.text: return
                cmd_to_enable = response.text.strip().lower().replace("/", "").replace("!", "")
                
                disabled_list = db.get("global_settings", {}).get("disabled_cmds", [])
                if cmd_to_enable not in disabled_list:
                    return await conv.send_message(f"**⚠️ | الأمر `{cmd_to_enable}` غير معطل أصلاً.**")
                
                db["global_settings"]["disabled_cmds"].remove(cmd_to_enable)
                save_db(db)
                await conv.send_message(f"**✅ | تم إعادة تفعيل الأمر `{cmd_to_enable}` في جميع المجموعات.**")
        except asyncio.TimeoutError: 
            await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "g_list_disabled":
        disabled_list = db.get("global_settings", {}).get("disabled_cmds", [])
        if not disabled_list:
            text_to_send = "**📜 | لا توجد أي أوامر معطلة على مستوى البوت حالياً.**"
        else:
            text_to_send = "**📜 | قائمة الأوامر المعطلة عاماً:**\n\n"
            # استخدام enumerate للترقيم
            text_to_send += "\n".join(f"{i+1}. `{cmd}`" for i, cmd in enumerate(disabled_list))
        
        # استخدام edit بدلاً من answer لتغيير الرسالة الحالية
        await event.edit(text_to_send, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:global_settings")])
