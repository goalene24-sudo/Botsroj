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
        # --- (تمت الإضافة) الزر الجديد ---
        [Button.inline("🌐 الإعدادات العامة", data="sudo_panel:global_settings")],
        [Button.inline("🔄 إعادة التشغيل", data="sudo_panel:restart"), Button.inline("🛑 إيقاف التشغيل", data="sudo_panel:shutdown")],
        [Button.inline("📁 تحميل قاعدة البيانات", data="sudo_panel:get_db")],
    ]
    return buttons

# --- نص الرسالة الرئيسية للوحة التحكم ---
SUDO_PANEL_TEXT = "**⚙️ | لوحة تحكم المطور**\n\n**أهلاً بك يا مطوري. اختر أحد الأقسام للتحكم بالبوت:**"

# --- معالج الأمر الرئيسي لفتح اللوحة ---
@client.on(events.NewMessage(pattern="^/لوحه$"))
async def open_sudo_panel(event):
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return
    await event.reply(SUDO_PANEL_TEXT, buttons=build_sudo_panel())


# --- معالج ضغطات الأزرار في لوحة التحكم ---
@client.on(events.CallbackQuery(pattern=b"^sudo_panel:"))
async def sudo_panel_callback(event):
    if event.sender_id not in config.SUDO_USERS:
        return await event.answer("🚫 | هذه اللوحة مخصصة للمطور فقط.", alert=True)

    action_parts = event.data.decode().split(':')
    action = action_parts[1]

    # ... (كل الأكواد السابقة تبقى كما هي من action 'main' إلى 'gadmin') ...
    
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
        group_count = sum(1 for key in db.keys() if isinstance(key, str) and key.startswith('-'))
        unique_users = set()
        for chat_id, chat_data in db.items():
            if isinstance(chat_data, dict) and "users" in chat_data:
                unique_users.update(chat_data["users"].keys())
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
                if response.text.strip().lower() == "الغاء": return await conv.send_message("**☑️ | تم إلغاء الإذاعة.**")
                await conv.send_message("**⏳ | سأبدأ الآن ببث الرسالة...**")
                successful, failed = 0, 0
                all_chats = [key for key in db.keys() if isinstance(key, str) and key.startswith('-')]
                for chat_id_str in all_chats:
                    try:
                        await client.send_message(int(chat_id_str), response.message)
                        successful += 1; await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Broadcast failed for chat {chat_id_str}: {e}"); failed += 1
                await conv.send_message(f"**📡 | اكتملت الإذاعة!**\n**- ✅ نجح:** `{successful}`\n**- ❌ فشل:** `{failed}`")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "get_db":
        await event.answer("📁 | جاري تحضير الملف...")
        try: await client.send_file(event.chat_id, "database.json", caption="**🗄️ | النسخة الاحتياطية من `database.json`**")
        except Exception as e: await event.reply(f"**حدث خطأ:**\n`{e}`")

    elif action == "gban":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🚫 | أرسل الآن ID المستخدم للحظر العام...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if response.text.strip().lower() == "الغاء": return await conv.send_message("**☑️ | تم إلغاء الأمر.**")
                try: user_id_to_ban = int(response.text.strip())
                except ValueError: return await conv.send_message("**⚠️ | ID غير صالح.**")
                await conv.send_message(f"**⏳ | سأقوم الآن بحظر `{user_id_to_ban}`...**")
                if "globally_banned" not in db: db["globally_banned"] = []
                if user_id_to_ban not in db["globally_banned"]:
                    db["globally_banned"].append(user_id_to_ban)
                    save_db(db)
                successful, failed = 0, 0
                all_chats = [key for key in db.keys() if isinstance(key, str) and key.startswith('-')]
                for chat_id_str in all_chats:
                    try:
                        await client.edit_permissions(int(chat_id_str), user_id_to_ban, view_messages=False)
                        successful += 1; await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"GBan failed for chat {chat_id_str}: {e}"); failed += 1
                await conv.send_message(f"**🚫 | اكتمل الحظر العام!**\n**- ✅ تم الحظر في:** `{successful}`\n**- ❌ فشل في:** `{failed}`")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()
        
    elif action == "gadmin":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🧑‍✈️ | أرسل الآن ID المستخدم للترقية العامة...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if response.text.strip().lower() == "الغاء": return await conv.send_message("**☑️ | تم إلغاء الأمر.**")
                try: user_id_to_promote = int(response.text.strip())
                except ValueError: return await conv.send_message("**⚠️ | ID غير صالح.**")
                await conv.send_message(f"**⏳ | سأقوم الآن بترقية `{user_id_to_promote}`...**")
                promoted_in = 0
                all_chats = [key for key in db.keys() if isinstance(key, str) and key.startswith('-')]
                for chat_id_str in all_chats:
                    db[chat_id_str].setdefault("bot_admins", [])
                    if user_id_to_promote not in db[chat_id_str]["bot_admins"]:
                        db[chat_id_str]["bot_admins"].append(user_id_to_promote)
                        promoted_in += 1
                save_db(db)
                await conv.send_message(f"**🧑‍✈️ | اكتملت الترقية!**\n**- ✅ تمت الترقية في:** `{promoted_in}` **مجموعة.**")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "db_maint":
        await event.edit("**🛠️ | جاري فحص قاعدة البيانات...**")
        inactive_chats = []
        all_chats = [key for key in db.keys() if isinstance(key, str) and key.startswith('-')]
        for chat_id_str in all_chats:
            try:
                await client.get_entity(int(chat_id_str)); await asyncio.sleep(1)
            except Exception as e:
                inactive_chats.append(chat_id_str)
                print(f"DB Maint found inactive chat {chat_id_str}: {e}")
        if not inactive_chats:
            return await event.edit("**✅ | قاعدة البيانات نظيفة!**", buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
        for chat_id_str in inactive_chats:
            if chat_id_str in db: del db[chat_id_str]
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
                chat_id_str = response.text.strip()
                chat_data = db.get(chat_id_str)
                if not chat_data: return await conv.send_message("**لم يتم العثور على بيانات لهذه المجموعة.**")
                report = f"**📄 | تقرير المجموعة `{chat_id_str}`**\n"
                report += f"- أعضاء مسجلين: {len(chat_data.get('users', {}))}\n"
                report += f"- أدمنية: {len(chat_data.get('bot_admins', []))}\n"
                await conv.send_message(report)
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**"); await event.answer()

    elif action == "inspect_user":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**👤 | أرسل الآن ID المستخدم...**")
                response = await conv.get_response()
                user_id_str = response.text.strip()
                report = f"**📄 | تقرير المستخدم `{user_id_str}`**\n"
                is_gbanned = user_id_str in (str(uid) for uid in db.get("globally_banned", []))
                report += f"- الحظر العام: {'محظور 🚫' if is_gbanned else 'غير محظور ✅'}\n"
                groups_found_in, total_msgs = [], 0
                for chat_id, chat_data in db.items():
                    if isinstance(chat_data, dict) and "users" in chat_data and user_id_str in chat_data["users"]:
                        groups_found_in.append(chat_id)
                        total_msgs += chat_data["users"][user_id_str].get("msg_count", 0)
                report += f"- مجموع الرسائل: {total_msgs}\n- موجود في: `{len(groups_found_in)}` مجموعة\n"
                await conv.send_message(report)
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**"); await event.answer()

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
                await conv.send_message("**🚫 | أرسل الآن اسم الأمر الذي تريد تعطيله على مستوى البوت بالكامل...**")
                response = await conv.get_response()
                cmd_to_disable = response.text.strip().lower()
                
                db.setdefault("global_settings", {}).setdefault("disabled_cmds", [])
                if cmd_to_disable in db["global_settings"]["disabled_cmds"]:
                    return await conv.send_message(f"**الأمر `{cmd_to_disable}` معطل بالفعل.**")
                
                db["global_settings"]["disabled_cmds"].append(cmd_to_disable)
                save_db(db)
                await conv.send_message(f"**✅ | تم تعطيل الأمر `{cmd_to_disable}` في جميع المجموعات.**")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "g_enable_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**✅ | أرسل الآن اسم الأمر الذي تريد إعادة تفعيله...**")
                response = await conv.get_response()
                cmd_to_enable = response.text.strip().lower()
                
                disabled_list = db.get("global_settings", {}).get("disabled_cmds", [])
                if cmd_to_enable not in disabled_list:
                    return await conv.send_message(f"**الأمر `{cmd_to_enable}` غير معطل أصلاً.**")
                
                db["global_settings"]["disabled_cmds"].remove(cmd_to_enable)
                save_db(db)
                await conv.send_message(f"**✅ | تم إعادة تفعيل الأمر `{cmd_to_enable}` في جميع المجموعات.**")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        await event.answer()

    elif action == "g_list_disabled":
        disabled_list = db.get("global_settings", {}).get("disabled_cmds", [])
        if not disabled_list:
            text_to_send = "**📜 | لا توجد أي أوامر معطلة على مستوى البوت حالياً.**"
        else:
            text_to_send = "**📜 | قائمة الأوامر المعطلة عاماً:**\n\n"
            text_to_send += "\n".join(f"- `{cmd}`" for cmd in disabled_list)
        
        await event.answer(text_to_send, alert=True)
