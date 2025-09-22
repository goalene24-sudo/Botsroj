import asyncio
import os
import sys
import json
from telethon import events, Button
from bot import client, StartTime
import config

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from sqlalchemy import func, delete, text
from database import AsyncDBSession
from models import Chat, User, GlobalSetting, BotAdmin

# --- استيراد الدوال المساعدة من ملف utils ---
from .utils import get_uptime_string, get_global_setting, set_global_setting


# --- الدالة الرئيسية لبناء أزرار لوحة التحكم ---
def build_sudo_panel():
    buttons = [
        [Button.inline("📊 الإحصائيات العامة", data="sudo_panel:stats")],
        [Button.inline("📢 قسم الإذاعة", data="sudo_panel:broadcast")],
        [Button.inline("🚫 الحظر العام", data="sudo_panel:gban"), Button.inline("🧑‍✈️ الترقيات العامة", data="sudo_panel:gadmin")],
        [Button.inline("🏙️ إدارة المجموعات", data="sudo_panel:manage_groups")], # <-- تمت إضافة الزر الجديد هنا
        [Button.inline("🛠️ الصيانة", data="sudo_panel:db_maint"), Button.inline("🔍 فحص البيانات", data="sudo_panel:inspect")],
        [Button.inline("🌐 الإعدادات العامة", data="sudo_panel:global_settings")],
        [Button.inline("📝 الأوامر المخصصة", data="sudo_panel:custom_cmds")],
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
        async with AsyncDBSession() as session:
            group_count = await session.scalar(select(func.count(Chat.id)))
            user_count = await session.scalar(select(func.count(func.distinct(User.user_id))))

        stats_text = f"""**📊 | الإحصائيات العامة للبوت**

**- مدة التشغيل (Uptime):** `{uptime}`
**- عدد المجموعات المسجلة:** `{group_count}` مجموعة
**- عدد المستخدمين الفريدين:** `{user_count}` مستخدم
"""
        await event.edit(stats_text, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
    
    # ===================================================================
    # | START OF NEW CODE | بداية الكود الجديد لإدارة المجموعات          |
    # ===================================================================
    elif action == "manage_groups":
        groups_text = "**🏙️ | قسم إدارة المجموعات**\n\n**اختر الإجراء المطلوب:**"
        groups_buttons = [
            [Button.inline("📜 عرض كل المجموعات", data="sudo_panel:list_all_groups")],
            [Button.inline("▶️ تفعيل بوت بمجموعة", data="sudo_panel:activate_group"), Button.inline("⏸️ إيقاف بوت بمجموعة", data="sudo_panel:deactivate_group")],
            [Button.inline("🔙 رجوع", data="sudo_panel:main")]
        ]
        await event.edit(groups_text, buttons=groups_buttons)

    elif action == "list_all_groups":
        await event.answer("📜 | جاري جلب قائمة المجموعات...")
        async with AsyncDBSession() as session:
            all_chats = (await session.execute(select(Chat))).scalars().all()
        
        if not all_chats:
            return await event.edit("**🗄️ | قاعدة البيانات فارغة، لا توجد مجموعات.**", buttons=[Button.inline("🔙 رجوع", data="sudo_panel:manage_groups")])
            
        report = "**📋 | قائمة بكل المجموعات المسجلة:**\n\n"
        for chat in all_chats:
            status = "نشط ✅" if chat.is_active else "غير نشط ⏸️"
            try:
                entity = await client.get_entity(chat.id)
                chat_title = entity.title
            except Exception:
                chat_title = "اسم غير معروف (البوت مطرود)"
            
            report += f"**- الاسم:** {chat_title}\n"
            report += f"** - ID:** `{chat.id}`\n"
            report += f"** - الحالة:** {status}\n"
            report += "-"*20 + "\n"

        # إرسال التقرير كرسالة جديدة لأنه قد يكون طويلاً جداً
        await client.send_message(event.chat_id, report)
        await event.answer("✅ | تم إرسال القائمة.")

    elif action in ["activate_group", "deactivate_group"]:
        action_text = "تفعيله" if action == "activate_group" else "إيقافه"
        target_state = True if action == "activate_group" else False
        
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message(f"**أرسل الآن ID المجموعة التي تريد {action_text}.**")
                response = await conv.get_response()
                try:
                    chat_id = int(response.text.strip())
                except ValueError:
                    return await conv.send_message("**⚠️ | ID غير صالح. يجب أن يكون رقماً.**")
                
                async with AsyncDBSession() as session:
                    chat_to_update = (await session.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
                    if not chat_to_update:
                        return await conv.send_message("**⚠️ | لم يتم العثور على مجموعة بهذا الـ ID.**")
                    
                    chat_to_update.is_active = target_state
                    await session.commit()
                    await conv.send_message(f"**✅ | تم {action_text} في المجموعة `{chat_id}` بنجاح.**")

        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
    # ===================================================================
    # | END OF NEW CODE | نهاية الكود الجديد                               |
    # ===================================================================
        
    elif action == "broadcast":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**📢 | أرسل الآن رسالة الإذاعة...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if not response.text or response.text.strip().lower() == "الغاء":    
                    return await conv.send_message("**☑️ | تم إلغاء الإذاعة.**")
                
                await conv.send_message("**⏳ | سأبدأ الآن ببث الرسالة...**")
                successful, failed = 0, 0
                async with AsyncDBSession() as session:
                    result = await session.execute(select(Chat.id))
                    all_chat_ids = result.scalars().all()

                for chat_id in all_chat_ids:
                    try:
                        await client.send_message(chat_id, response.message)
                        successful += 1; await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Broadcast failed for chat {chat_id}: {e}"); failed += 1
                await conv.send_message(f"**📡 | اكتملت الإذاعة!**\n**- ✅ نجح:** `{successful}`\n**- ❌ فشل:** `{failed}`")
        except asyncio.TimeoutError:    
            await event.reply("**⏰ | انتهى الوقت.**")
        
    elif action == "get_db":
        await event.answer("📁 | جاري تحضير ودمج بيانات القاعدة...")
        db_path = "surooj.db"
        
        if not os.path.exists(db_path):
            return await client.send_message(event.chat_id, f"**❌ | خطأ: لم يتم العثور على الملف `{db_path}`!**")
        
        try:
            async with AsyncDBSession() as session:
                async with session.begin():
                    await session.execute(text("PRAGMA wal_checkpoint(FULL);"))
            
            await client.send_file(
                event.chat_id, 
                db_path, 
                caption="**🗄️ | النسخة الاحتياطية المحدثة من قاعدة البيانات**"
            )
            await event.delete()

        except Exception as e:
            await client.send_message(event.chat_id, f"**❌ | حدث خطأ أثناء تحضير أو إرسال الملف:**\n`{e}`")
        return

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
                
                banned_list = await get_global_setting("globally_banned", [])
                if user_id_to_ban not in banned_list:
                    banned_list.append(user_id_to_ban)
                    await set_global_setting("globally_banned", banned_list)

                successful, failed = 0, 0
                async with AsyncDBSession() as session:
                    result = await session.execute(select(Chat.id))
                    all_chat_ids = result.scalars().all()

                for chat_id in all_chat_ids:
                    try:
                        await client.edit_permissions(chat_id, user_id_to_ban, view_messages=False)
                        successful += 1; await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"GBan failed for chat {chat_id}: {e}"); failed += 1
                await conv.send_message(f"**🚫 | اكتمل الحظر العام!**\n**- ✅ تم الحظر في:** `{successful}`\n**- ❌ فشل في:** `{failed}`")
        except asyncio.TimeoutError:    
            await event.reply("**⏰ | انتهى الوقت.**")
        
    elif action == "gadmin":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🧑‍✈️ | أرسل الآن ID المستخدم للترقية العامة...**\n**(للإلغاء، أرسل `الغاء`)**")
                response = await conv.get_response()
                if not response.text or response.text.strip().lower() == "الغاء": return await conv.send_message("**☑️ | تم إلغاء الأمر.**")
                try: user_id_to_promote = int(response.text.strip())
                except ValueError: return await conv.send_message("**⚠️ | ID غير صالح.**")
                await conv.send_message(f"**⏳ | سأقوم الآن بترقية `{user_id_to_promote}`...**")
                promoted_in = 0
                async with AsyncDBSession() as session:
                    result = await session.execute(select(Chat.id))
                    all_chat_ids = result.scalars().all()
                    for chat_id in all_chat_ids:
                        res = await session.execute(select(BotAdmin).where(BotAdmin.chat_id == chat_id, BotAdmin.user_id == user_id_to_promote))
                        if not res.scalar_one_or_none():
                            session.add(BotAdmin(chat_id=chat_id, user_id=user_id_to_promote))
                            promoted_in += 1
                    await session.commit()
                await conv.send_message(f"**🧑‍✈️ | اكتملت الترقية!**\n**- ✅ تمت الترقية في:** `{promoted_in}` **مجموعة جديدة.**")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        
    elif action == "db_maint":
        await event.edit("**🛠️ | جاري فحص قاعدة البيانات...**")
        inactive_chat_ids = []
        async with AsyncDBSession() as session:
            result = await session.execute(select(Chat.id))
            all_chat_ids = result.scalars().all()
            for chat_id in all_chat_ids:
                try:
                    await client.get_entity(chat_id); await asyncio.sleep(1)
                except Exception:
                    inactive_chat_ids.append(chat_id)
            if not inactive_chat_ids:
                return await event.edit("**✅ | قاعدة البيانات نظيفة!**", buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
            await session.execute(delete(Chat).where(Chat.id.in_(inactive_chat_ids)))
            await session.commit()
        await event.edit(f"**🗑️ | اكتملت الصيانة!**\n**تم تنظيف `{len(inactive_chat_ids)}` مجموعة غير نشطة.**", buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])

    elif action == "inspect":
        inspect_text = "**🔍 | قسم فحص البيانات**\n\n**اختر نوع البيانات:**"
        inspect_buttons = [[Button.inline("فحص مجموعة 🏙️", data="sudo_panel:inspect_group"), Button.inline("فحص مستخدم 👤", data="sudo_panel:inspect_user")], [Button.inline("🔙 رجوع", data="sudo_panel:main")]]
        await event.edit(inspect_text, buttons=inspect_buttons)

    elif action == "inspect_group":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🏙️ | أرسل الآن ID المجموعة...**")
                response = await conv.get_response()
                try: chat_id = int(response.text.strip())
                except ValueError: return await conv.send_message("**ID غير صالح.**")
                async with AsyncDBSession() as session:
                    chat_data = (await session.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
                    if not chat_data: return await conv.send_message("**لم يتم العثور على بيانات لهذه المجموعة.**")
                    user_count = await session.scalar(select(func.count(User.id)).where(User.chat_id == chat_id))
                    admin_count = await session.scalar(select(func.count(BotAdmin.id)).where(BotAdmin.chat_id == chat_id))
                report = f"**📄 | تقرير المجموعة `{chat_id}`**\n- أعضاء مسجلين: {user_count}\n- أدمنية البوت: {admin_count}\n"
                await conv.send_message(report)
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        
    elif action == "inspect_user":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**👤 | أرسل الآن ID المستخدم...**")
                response = await conv.get_response()
                try: user_id = int(response.text.strip())
                except ValueError: return await conv.send_message("**ID غير صالح.**")
                report = f"**📄 | تقرير المستخدم `{user_id}`**\n"
                banned_list = await get_global_setting("globally_banned", [])
                is_gbanned = user_id in banned_list
                report += f"- الحظر العام: {'محظور 🚫' if is_gbanned else 'غير محظور ✅'}\n"
                async with AsyncDBSession() as session:
                    total_msgs_res = await session.execute(select(func.sum(User.msg_count)).where(User.user_id == user_id))
                    total_msgs = total_msgs_res.scalar() or 0
                    group_count_res = await session.execute(select(func.count(User.id)).where(User.user_id == user_id))
                    group_count = group_count_res.scalar() or 0
                report += f"- مجموع الرسائل: {total_msgs}\n- موجود في: `{group_count}` مجموعة\n"
                await conv.send_message(report)
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")
        
    elif action == "global_settings":
        disabled_cmds = await get_global_setting("disabled_cmds", [])
        settings_text = "**🌐 | الإعدادات العامة للبوت**\n\n**اختر الإجراء:**"
        settings_buttons = [[Button.inline("🚫 تعطيل أمر عام", data="sudo_panel:g_disable_cmd"), Button.inline("✅ تفعيل أمر عام", data="sudo_panel:g_enable_cmd")], [Button.inline(f"📜 عرض الأوامر المعطلة ({len(disabled_cmds)})", data="sudo_panel:g_list_disabled")], [Button.inline("🔙 رجوع", data="sudo_panel:main")]]
        await event.edit(settings_text, buttons=settings_buttons)

    elif action == "g_disable_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**🚫 | أرسل الآن اسم الأمر لتعطيله...**")
                response = await conv.get_response()
                if not response.text: return
                cmd_to_disable = response.text.strip().lower().replace("/", "").replace("!", "")
                disabled_list = await get_global_setting("disabled_cmds", [])
                if cmd_to_disable in disabled_list:
                    return await conv.send_message(f"**⚠️ | الأمر `{cmd_to_disable}` معطل بالفعل.**")
                disabled_list.append(cmd_to_disable)
                await set_global_setting("disabled_cmds", disabled_list)
                await conv.send_message(f"**✅ | تم تعطيل الأمر `{cmd_to_disable}`.**")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")

    elif action == "g_enable_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**✅ | أرسل الآن اسم الأمر لتفعيله...**")
                response = await conv.get_response()
                if not response.text: return
                cmd_to_enable = response.text.strip().lower().replace("/", "").replace("!", "")
                disabled_list = await get_global_setting("disabled_cmds", [])
                if cmd_to_enable not in disabled_list:
                    return await conv.send_message(f"**⚠️ | الأمر `{cmd_to_enable}` غير معطل أصلاً.**")
                disabled_list.remove(cmd_to_enable)
                await set_global_setting("disabled_cmds", disabled_list)
                await conv.send_message(f"**✅ | تم تفعيل الأمر `{cmd_to_enable}`.**")
        except asyncio.TimeoutError: await event.reply("**⏰ | انتهى الوقت.**")

    elif action == "g_list_disabled":
        disabled_list = await get_global_setting("disabled_cmds", [])
        if not disabled_list:
            text_to_send = "**📜 | لا توجد أوامر معطلة.**"
        else:
            text_to_send = "**📜 | الأوامر المعطلة:**\n\n" + "\n".join(f"- `{cmd}`" for cmd in disabled_list)
        await event.edit(text_to_send, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:global_settings")])

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
                
                placeholders_guide = ("**حسناً، الآن أرسل النص الذي سيرد به البوت.**\n\n"
                                      "**يمكنك استخدام المتغيرات التالية:**\n"
                                      "`{user_first_name}` - الاسم الأول\n"
                                      "`{user_mention}` - منشن للعضو")
                await conv.send_message(placeholders_guide)
                cmd_reply_msg = await conv.get_response()
                cmd_reply_text = cmd_reply_msg.text

                ask_button_msg = await conv.send_message(
                    "**هل تريد إضافة زر لهذا الأمر في قائمة الأوامر الرئيسية؟**",
                    buttons=[[Button.inline("✅ نعم", data="yes"), Button.inline("❌ لا", data="no")]]
                )
                
                button_choice_event = await conv.wait_event(
                    events.CallbackQuery(func=lambda e: e.sender_id == event.sender_id)
                )
                await button_choice_event.answer()
                button_choice = button_choice_event.data.decode()
                await ask_button_msg.delete()

                command_data = {"reply": cmd_reply_text}
                if button_choice == "yes":
                    await conv.send_message("**أرسل الآن النص الذي سيظهر على الزر.**\n\n**مثال: `قناتنا`**")
                    button_text_msg = await conv.get_response()
                    button_text = button_text_msg.text.strip()
                    command_data["button_text"] = button_text
                    command_data["display_mode"] = "edit" 
                else:
                    command_data["display_mode"] = "popup" 
                
                custom_commands = await get_global_setting("custom_commands", {})
                custom_commands[cmd_name] = command_data
                await set_global_setting("custom_commands", custom_commands)
                await conv.send_message(f"**✅ | تم حفظ الأمر `{cmd_name}` بنجاح!**")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        
    elif action == "del_cmd":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**أرسل اسم الأمر الذي تريد حذفه.**")
                cmd_name_msg = await conv.get_response()
                cmd_name = cmd_name_msg.text.strip().lower()
                custom_commands = await get_global_setting("custom_commands", {})
                if cmd_name in custom_commands:
                    del custom_commands[cmd_name]
                    await set_global_setting("custom_commands", custom_commands)
                    await conv.send_message(f"**🗑️ | تم حذف الأمر `{cmd_name}` بنجاح.**")
                else:
                    await conv.send_message(f"**⚠️ | لم يتم العثور على أمر بهذا الاسم.**")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
            
    elif action == "list_cmds":
        custom_commands = await get_global_setting("custom_commands", {})
        if not custom_commands:
            text_to_send = "**📜 | لا توجد أي أوامر مخصصة حالياً.**"
        else:
            text_to_send = "**📜 | قائمة الأوامر المخصصة:**\n\n"
            text_to_send += "\n".join(f"- `{cmd}`" for cmd in custom_commands.keys())
        
        await event.edit(text_to_send, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:custom_cmds")])
