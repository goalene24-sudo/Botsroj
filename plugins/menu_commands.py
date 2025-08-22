from telethon import events, Button
from bot import client
from .utils import check_activation, MAIN_MENU_BUTTONS, GEMINI_ENABLED, has_bot_permission, build_protection_menu
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT, SHOP_MENU_TEXT
)

@client.on(events.NewMessage(pattern="^(الالعاب|التسلية)$"))
async def fun_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    fun_text = FUN_MENU_TEXT
    if GEMINI_ENABLED:
        fun_text += "\n\n**الذكي مال المجموعة:**\n**`اسأل + سؤالك`**"
    await event.reply(fun_text)

@client.on(events.NewMessage(pattern="^ملفي الشخصي$"))
async def profile_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(PROFILE_MENU_TEXT)

@client.on(events.NewMessage(pattern="^الاجتماعية$"))
async def social_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SOCIAL_MENU_TEXT)

@client.on(events.NewMessage(pattern="^المتجر$"))
async def shop_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SHOP_MENU_TEXT)

@client.on(events.NewMessage(pattern="^(الادوات|أدوات|ادوات المجموعة)$"))
async def tools_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(TOOLS_MENU_TEXT)

@client.on(events.NewMessage(pattern="^(الخدمات|دينيه)$"))
async def services_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SERVICES_MENU_TEXT)

@client.on(events.NewMessage(pattern="^الردود$"))
async def replies_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(REPLIES_MENU_TEXT)

# --- الأمر الخاص بقائمة الحماية (يبقى كما هو بأزراره الخاصة) ---
@client.on(events.NewMessage(pattern="^الحماية$"))
async def protection_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): 
        return await event.reply("**قسم الحماية بس للمشرفين والأدمنية.**")
    
    await event.reply(
        "**🛡️ قائمة الحماية التفاعلية** 🛡️\n**دوس على أي دگمة حتى تغير حالتها.**",
        buttons=await build_protection_menu(event.chat_id)
    )
