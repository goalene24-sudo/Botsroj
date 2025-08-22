# plugins/menu_commands.py
from telethon import events, Button
from bot import client
from .utils import check_activation, MAIN_MENU_BUTTONS, GEMINI_ENABLED
from .shop import SHOP_ITEMS
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT
)

@client.on(events.NewMessage(pattern="^(الالعاب|التسلية)$"))
async def fun_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    fun_text = FUN_MENU_TEXT
    if GEMINI_ENABLED:
        fun_text += "\n\n**الذكي مال المجموعة:**\n**`اسأل + سؤالك`**"
    await event.reply(fun_text, buttons=MAIN_MENU_BUTTONS)

@client.on(events.NewMessage(pattern="^ملفي الشخصي$"))
async def profile_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(PROFILE_MENU_TEXT, buttons=MAIN_MENU_BUTTONS)

@client.on(events.NewMessage(pattern="^الاجتماعية$"))
async def social_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SOCIAL_MENU_TEXT, buttons=MAIN_MENU_BUTTONS)

@client.on(events.NewMessage(pattern="^المتجر$"))
async def shop_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
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
    await event.reply(shop_text, buttons=MAIN_MENU_BUTTONS)

@client.on(events.NewMessage(pattern="^(الادوات|أدوات)$"))
async def tools_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(TOOLS_MENU_TEXT, buttons=MAIN_MENU_BUTTONS)

@client.on(events.NewMessage(pattern="^(الخدمات|دينيه)$"))
async def services_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(SERVICES_MENU_TEXT, buttons=MAIN_MENU_BUTTONS)

@client.on(events.NewMessage(pattern="^الردود$"))
async def replies_menu_command(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(REPLIES_MENU_TEXT, buttons=MAIN_MENU_BUTTONS)
