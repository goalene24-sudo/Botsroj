# plugins/core.py
import asyncio
from datetime import datetime
from telethon import events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from bot import client
import config
# --- [تم التحديث] ---
from .utils import (
    db, save_db, is_admin, check_activation, MAIN_MENU_MESSAGE,
    is_command_enabled, build_main_menu_buttons # استبدال MAIN_MENU_BUTTONS بالدالة
)

WELCOMED_RECENTLY = set()

@client.on(events.ChatAction)
async def chat_action_handler(event):
    me = await client.get_me()
    chat_id = event.chat_id
    if event.user_added and event.user_id == me.id:
        if chat_id in WELCOMED_RECENTLY: return
        WELCOMED_RECENTLY.add(chat_id)
        chat = await event.get_chat()
        chat_id_str = str(chat_id)
        if chat_id_str not in db: db[chat_id_str] = {}
        try:
            member_count = (await client.get_participants(chat_id, limit=0)).total
            admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
            admin_count = len(admin_list)
            bot_pfp = await client.get_profile_photos('me', limit=1)
        except Exception as e: print(f"لا يمكن جلب معلومات المجموعة {chat_id}: {e}"); return
        welcome_text = (f"**🚨 هلا والله! آني {me.first_name} وصلت حتى احمي المجموعة.**\n\n"
                        f"**📊 اسم المجموعة: {chat.title}**\n"
                        f"**👥 عددكم: {member_count} نفر**\n"
                        f"**🛡️ المشرفين: {admin_count} مدير**\n"
                        f"**💻 المطور مالتي: @tit_50**\n\n"
                        "**ارفعني مشرف وانطيني الصلاحيات كاملة، ودوس الدگمة الجوه حتى تشوف العجب! 😉**")
        activate_button = Button.inline("✅ تفعيل البوت ✅", data=f"activate_{chat_id}")
        if bot_pfp: await client.send_file(chat_id, bot_pfp[0], caption=welcome_text, buttons=activate_button)
        else: await client.send_message(chat_id, welcome_text, buttons=activate_button)
        await asyncio.sleep(10)
        if chat_id in WELCOMED_RECENTLY: WELCOMED_RECENTLY.remove(chat_id)
    
    elif event.user_joined and not event.user_id == me.id:
        if not await check_activation(event.chat_id): return
        # التحقق إذا كان الترحيب مفعلاً
        if not is_command_enabled(event.chat_id, "welcome_enabled"):
            return

        chat = await event.get_chat()
        new_user = await event.get_user()
        chat_id_str = str(event.chat_id)
        
        custom_welcome = db.get(chat_id_str, {}).get("welcome_message")
        if custom_welcome:
            welcome_text = custom_welcome.format(
                user=f"[{new_user.first_name}](tg://user?id={new_user.id})",
                group=chat.title
            )
        else:
            welcome_text = f"**هلا بالضلع الجديد [{new_user.first_name}](tg://user?id={new_user.id}) نورت الكروب يا غالي 🥳**"
        
        buttons = Button.inline("📜 عرض القوانين", data="show_rules")
        await client.send_message(event.chat_id, f"**{welcome_text}**", buttons=buttons)
    
    elif (event.user_kicked or event.user_left) and event.user_id == me.id:
        chat_id_str = str(event.chat_id)
        if chat_id_str in db:
            db[chat_id_str]["is_paused"] = True
            save_db(db)
        print(f"تمت إزالة البوت من المجموعة {event.chat_id} وتم إيقافه فيها تلقائياً.")

@client.on(events.NewMessage(pattern="^(تفعيل|ايقاف)$"))
async def toggle_bot_status(event):
    if event.is_private: return
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين يمعود. 😒**")
    chat_id_str, action, me = str(event.chat_id), event.raw_text, await client.get_me()
    if chat_id_str not in db: db[chat_id_str] = {}
    if action == "ايقاف":
        db[chat_id_str]["is_paused"] = True
        save_db(db); await event.reply("**🔴 خوش، سكتت. لمن تريدني ارجع اشتغل، بس اكتب `تفعيل`.**")
    else:
        if not await is_admin(event.chat_id, me.id): return await event.reply("**يمعود ارفعني مشرف أول شي يله اگدر اشتغل! 🤷‍♂️**")
        db[chat_id_str]["is_paused"] = False
        save_db(db)
        await event.reply("**🟢 رجعتلكم! يلا شنو الأوامر؟**")

@client.on(events.NewMessage(pattern='^الاوامر$'))
async def main_menu_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- [تم التحديث] ---
    # استدعاء الدالة لبناء الأزرار بشكل ديناميكي
    buttons = build_main_menu_buttons()
    await event.reply(f"**{MAIN_MENU_MESSAGE}**", buttons=buttons)
