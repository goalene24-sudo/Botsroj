from telethon import events, Button
from bot import client, StartTime
from .utils import (
    db, save_db, is_admin, has_bot_permission,
    GEMINI_ENABLED, MAIN_MENU_MESSAGE, MAIN_MENU_BUTTONS,
    build_protection_menu, get_uptime_string
)
from .interactive_callbacks import handle_interactive_callback
from .services import SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT, ADMIN_COMMANDS_INFO_TEXT,
    SHOP_MENU_TEXT
)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    query_data = event.data.decode('utf-8')
    
    main_menus = [
        "fun_menu", "profile_menu", "shop_menu", "tools_menu",
        "services_menu", "replies_menu", "about_menu", "back_to_main",
        "protection_menu", "admin_cmds_info", "seerah_main", "hisn_main",
        "social_menu"
    ]

    if query_data in main_menus:
        text_to_show = None
        buttons_to_show = MAIN_MENU_BUTTONS

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
                if not chat_info.get("is_paused", False) and await is_admin(int(chat_id_str), 'me'):
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

        elif query_data == "admin_cmds_info":
            return await event.edit(ADMIN_COMMANDS_INFO_TEXT, buttons=[[Button.inline("🔙 رجوع لقائمة الحماية", data="protection_menu")]])
        
        elif query_data == "seerah_main":
            text = "**صلى الله على محمد ﷺ**\n\n**اختر مرحلة من السيرة النبوية الشريفة لعرضها:**"
            buttons = []
            for key, value in SEERAH_STAGES.items():
                buttons.append([Button.inline(value["button"], data=f"seerah:{key}")])
            return await event.edit(text, buttons=buttons)

        elif query_data == "hisn_main":
            text = "**حصن المسلم**\n\n**اختر الدعاء الذي تريد عرضه:**"
            buttons = []
            for key, value in HISN_ALMUSLIM.items():
                buttons.append([Button.inline(value["button"], data=f"hisn:{key}")])
            return await event.edit(text, buttons=buttons)
        
        if text_to_show:
            await event.edit(text_to_show, buttons=buttons_to_show)

    else:
        await handle_interactive_callback(event)
