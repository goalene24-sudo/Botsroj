# plugins/callbacks.py
from telethon import events, Button
from datetime import datetime
from bot import client, StartTime
from .utils import (
    db, save_db, is_admin, has_bot_permission,
    GEMINI_ENABLED, MAIN_MENU_MESSAGE, MAIN_MENU_BUTTONS,
    build_protection_menu
)
from .shop import SHOP_ITEMS
from .interactive_callbacks import handle_interactive_callback
from .services import SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT, ADMIN_COMMANDS_INFO_TEXT
)

def get_uptime_string(start_time):
    uptime_delta = datetime.now() - start_time
    days = uptime_delta.days
    hours, rem = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = ""
    if days > 0: uptime_str += f"{days} يوم و "
    if hours > 0: uptime_str += f"{hours} ساعة و "
    if minutes > 0: uptime_str += f"{minutes} دقيقة"
    return uptime_str.strip().strip('و ') or "بضع ثواني"


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
        # --- (التعديل الرئيسي هنا) ---
        # بدلاً من عرض زر "عودة"، سنعرض دائماً الأزرار الرئيسية
        # ما عدا في بعض الحالات الخاصة مثل قائمة الحماية
        
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
            shop_text = "**🛒 متجر سُـرُوچ** 🛒\n\n**أهلاً بك في المتجر! هنا يمكنك إنفاق نقاطك لشراء امتيازات رائعة.**\n\n"
            for item_name, details in SHOP_ITEMS.items():
                shop_text += f"**▫️ {item_name.title()}:** (`{details['price']}` **نقطة**)\n"
            
            shop_text += "\n**--- تعليمات ---**"
            shop_text += "\n**للشراء:** `شراء [اسم الغرض]`"
            if "تخصيص لقب" in SHOP_ITEMS:
                shop_text += "\n**لوضع اللقب:** `ضع لقبي [اللقب]`"
            
            shop_text += "\n\n**🏦 بنك المجموعة:**"
            shop_text += "\n**- `ايداع [مبلغ]`:** لإيداع نقاطك."
            shop_text += "\n**- `سحب [مبلغ]`:** لسحب نقاطك."
            shop_text += "\n**- `رصيدي بالبنك`:** لمعرفة رصيدك والأرباح."
            text_to_show = shop_text

        elif query_data == "back_to_main":
            text_to_show = MAIN_MENU_MESSAGE
        
        # --- حالات خاصة تحتفظ بزر العودة الخاص بها ---
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
        
        # --- التنفيذ ---
        if text_to_show:
            await event.edit(text_to_show, buttons=buttons_to_show)

    else:
        await handle_interactive_callback(event)
