# plugins/callbacks.py
from telethon import events, Button
from bot import client, StartTime
from .utils import (
    db, save_db, is_admin, has_bot_permission,
    GEMINI_ENABLED, MAIN_MENU_MESSAGE, build_main_menu_buttons,
    build_protection_menu, get_uptime_string
)
from .interactive_callbacks import handle_interactive_callback
from .services import SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT,
    SHOP_MENU_TEXT
)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    query_data = event.data.decode('utf-8')
    
    main_menus = [
        "fun_menu", "profile_menu", "shop_menu", "tools_menu",
        "services_menu", "replies_menu", "about_menu", "back_to_main",
        "protection_menu", "seerah_main", "hisn_main",
        "social_menu"
    ]

    if query_data in main_menus:
        text_to_show = None
        buttons_to_show = build_main_menu_buttons()

        if query_data == "fun_menu":
            text_to_show = FUN_MENU_TEXT
            if GEMINI_ENABLED:
                text_to_show += "\n\n**الذكي مال المجموعة:**\n**`اسأل + سؤالك`**"
        
        elif query_data == "profile_menu":
            text_to_show = PROFILE_MENU_TEXT
        
        elif query_data == "social_menu":
            text_to_show = SOCIAL_MENU_TEXT

        elif query_data == "tools_menu":
            text_to_show = TOOLS_MENU_TEXT

        elif query_data == "services_menu":
            text_to_show = SERVICES_MENU_TEXT
        
        elif query_data == "replies_menu":
            text_to_show = REPLIES_MENU_TEXT

        elif query_data == "shop_menu":
            text_to_show = SHOP_MENU_TEXT

        elif query_data == "back_to_main":
            text_to_show = MAIN_MENU_MESSAGE
        
        elif query_data == "about_menu":
            await event.answer("جاري حساب الإحصائيات...", alert=False)
            total_groups, all_users = 0, set()
            for chat_id_str in db:
                if not chat_id_str.startswith('-'): continue
                chat_info = db[chat_id_str]
                if not chat_info.get("is_paused", False): 
                    total_groups += 1
                    all_users.update(chat_info.get("users", {}).keys())
            uptime = get_uptime_string(StartTime)
            description = "أنا بوت خدمي وترفيهي وإداري،\nتم تطويري لكي البي جميع احتياجاتك."
            about_text = (
                f"**ℹ️ حول البوت سُـرُوچ**\n\n"
                f"**{description}**\n\n"
                f"**📈 إحصائياتي الحالية:**\n"
                f"**- أخدم حالياً في:** `{total_groups}` **مجموعة.**\n"
                f"**- أتفاعل مع:** `{len(all_users)}` **مستخدم.**\n"
                f"**- أعمل بدون توقف منذ:** `{uptime}`\n"
            )
            buttons = [[Button.url("👨‍💻 المطور", "https://t.me/tit_50")], [Button.inline("🔙 عودة", data="back_to_main")]]
            return await event.edit(about_text, buttons=buttons, link_preview=False)

        elif query_data == "protection_menu":
            if not await has_bot_permission(event): return await event.answer("**قسم الحماية بس للمشرفين والأدمنية.**", alert=True)
            return await event.edit("**🛡️ قائمة الحماية التفاعلية** 🛡️\n**دوس على أي دگمة حتى تغير حالتها.**", buttons=await build_protection_menu(event.chat_id))
        
        elif query_data == "seerah_main":
            text = "**صلى الله على محمد ﷺ**\n\n**اختر مرحلة من السيرة النبوية الشريفة لعرضها:**"
            buttons = []
            for key, value in SEERAH_STAGES.items():
                buttons.append([Button.inline(value["button"], data=f"seerah:{key}")])
            buttons.append([Button.inline("🔙 عودة", data="services_menu")])
            return await event.edit(text, buttons=buttons)

        elif query_data == "hisn_main":
            text = "**حصن المسلم**\n\n**اختر الدعاء الذي تريد عرضه:**"
            buttons = []
            for key, value in HISN_ALMUSLIM.items():
                buttons.append([Button.inline(value["button"], data=f"hisn:{key}")])
            buttons.append([Button.inline("🔙 عودة", data="services_menu")])
            return await event.edit(text, buttons=buttons)
        
        if text_to_show:
            await event.edit(text_to_show, buttons=buttons_to_show)

    elif not event.data.decode().startswith("admin_hub:"):
        await handle_interactive_callback(event)


# --- [تم التحديث] معالج جديد ومطور لضغطات أزرار الأوامر المخصصة ---
@client.on(events.CallbackQuery(pattern=b"^ccmd:(.+)"))
async def custom_command_button_handler(event):
    command_name = event.data.decode().split(':')[1]
    custom_commands = db.get("custom_commands", {})
    
    if command_name not in custom_commands:
        return await event.answer("⚠️ | عذراً، لم يعد هذا الأمر موجوداً.", alert=True)

    command_data = custom_commands[command_name]
    reply_template = command_data.get("reply")
    # إذا لم يتم تحديد طريقة العرض، نستخدم "منبثق" كافتراضي
    display_mode = command_data.get("display_mode", "popup") 

    if not reply_template:
        return await event.answer("⚠️ | لا يوجد نص رد لهذا الأمر.", alert=True)

    sender = await event.get_sender()
    chat = await event.get_chat()
    chat_id_str = str(chat.id)
    sender_id_str = str(sender.id)
    user_data = db.get(chat_id_str, {}).get("users", {}).get(sender_id_str, {})
    msg_count = user_data.get("msg_count", 0)
    points = user_data.get("points", 0)

    try:
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

        # التحقق من طريقة العرض المطلوبة
        if display_mode == "edit":
            # تعديل الرسالة مع زر رجوع
            back_button = Button.inline("🔙 رجوع", data="back_to_main")
            await event.edit(final_reply, buttons=back_button, parse_mode='md')
        else:
            # عرض رسالة منبثقة (السلوك الافتراضي)
            # الماركداون لا يعمل جيداً في الرسائل المنبثقة، لذا ننشئ نسخة مبسطة
            popup_reply = final_reply.replace(f"[{sender.first_name}](tg://user?id={sender.id})", sender.first_name)
            await event.answer(popup_reply, alert=True)

    except Exception as e:
        await event.answer(f"⚠️ | خطأ في عرض الرد: {e}", alert=True)
