from telethon import events, Button
from bot import client, StartTime
from .utils import (
    check_activation, db, is_admin, get_uptime_string, 
    GEMINI_ENABLED, has_bot_permission, build_protection_menu
)
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT, SHOP_MENU_TEXT
)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م1|الالعاب|التسلية)$"))
async def fun_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    fun_text = FUN_MENU_TEXT
    if GEMINI_ENABLED:
        fun_text += "\n\n**الذكي مال المجموعة:**\n**`اسأل + سؤالك`**"
    await event.reply(fun_text)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م3|ملفي الشخصي)$"))
async def profile_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(PROFILE_MENU_TEXT)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م2|التفاعل|الاجتماعية)$"))
async def social_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SOCIAL_MENU_TEXT)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م4|المتجر)$"))
async def shop_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SHOP_MENU_TEXT)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م5|الادوات|أدوات|ادوات المجموعة)$"))
async def tools_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(TOOLS_MENU_TEXT)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م7|الدينيه|الخدمات|الخدمات الدينيه)$"))
async def services_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SERVICES_MENU_TEXT)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م8|الردود)$"))
async def replies_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(REPLIES_MENU_TEXT)

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م6|الحماية)$"))
async def protection_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): 
        return await event.reply("**قسم الحماية بس للمشرفين والأدمنية.**")
    
    await event.reply(
        "**🛡️ قائمة الحماية التفاعلية** 🛡️\n**دوس على أي دگمة حتى تغير حالتها.**",
        buttons=await build_protection_menu(event.chat_id)
    )

@client.on(events.NewMessage(pattern=r"(?i)^\.?(م9|حول البوت)$"))
async def about_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
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
    buttons = [[Button.url("👨‍💻 المطور", "https://t.me/tit_50")]]
    await event.reply(about_text, buttons=buttons, link_preview=False)
