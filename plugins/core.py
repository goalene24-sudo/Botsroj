import asyncio
from telethon import events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from bot import client

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from sqlalchemy import delete
from database import AsyncDBSession  # تم التعديل هنا
from models import Chat, Vip, BotAdmin, Creator, SecondaryDev

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import (
    check_activation, is_command_enabled, build_main_menu_buttons, 
    MAIN_MENU_MESSAGE, is_admin
)
from .utils import get_or_create_chat, get_chat_setting # استيراد دوال إدارة المجموعة

WELCOMED_RECENTLY = set()

@client.on(events.ChatAction)
async def chat_action_handler(event):
    me = await client.get_me()
    chat_id = event.chat_id

    # عند إضافة البوت إلى مجموعة جديدة
    if event.user_added and event.user_id == me.id:
        if chat_id in WELCOMED_RECENTLY: 
            return
        WELCOMED_RECENTLY.add(chat_id)
        
        async with AsyncDBSession() as session:
            # التأكد من وجود سجل للمجموعة في قاعدة البيانات
            await get_or_create_chat(session, chat_id)

        try:
            chat = await event.get_chat()
            member_count = (await client.get_participants(chat_id, limit=0)).total
            admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
            admin_count = len(admin_list)
            bot_pfp = await client.get_profile_photos('me', limit=1)
        except Exception as e:
            print(f"لا يمكن جلب معلومات المجموعة {chat_id}: {e}")
            return
            
        welcome_text = (
            f"**🚨 هلا والله! آني {me.first_name} وصلت حتى احمي المجموعة.**\n\n"
            f"**📊 اسم المجموعة: {chat.title}**\n"
            f"**👥 عددكم: {member_count} نفر**\n"
            f"**🛡️ المشرفين: {admin_count} مدير**\n"
            f"**💻 المطور مالتي: @tit_50**\n\n"
            "**ارفعني مشرف وانطيني الصلاحيات كاملة، ودوس الدگمة الجوه حتى تشوف العجب! 😉**"
        )
        
        activate_button = Button.inline("✅ تفعيل البوت ✅", data=f"activate_{chat_id}")
        
        if bot_pfp:
            await client.send_file(chat_id, bot_pfp[0], caption=welcome_text, buttons=activate_button)
        else:
            await client.send_message(chat_id, welcome_text, buttons=activate_button)
        
        await asyncio.sleep(10)
        if chat_id in WELCOMED_RECENTLY:
            WELCOMED_RECENTLY.remove(chat_id)
    
    # عند انضمام عضو جديد
    elif event.user_joined and event.user_id != me.id:
        if not await check_activation(event.chat_id): 
            return
        
        # التحقق إذا كان الترحيب مفعلاً
        if not await is_command_enabled(event.chat_id, "welcome_enabled"):
            return

        chat = await event.get_chat()
        new_user = await event.get_user()
        
        custom_welcome = await get_chat_setting(event.chat_id, "welcome_message")
        
        if custom_welcome:
            welcome_text = custom_welcome.format(
                user=f"[{new_user.first_name}](tg://user?id={new_user.id})",
                group=chat.title
            )
        else:
            welcome_text = f"**هلا بالضلع الجديد [{new_user.first_name}](tg://user?id={new_user.id}) نورت الكروب يا غالي 🥳**"
        
        buttons = Button.inline("📜 عرض القوانين", data="show_rules")
        await client.send_message(event.chat_id, f"**{welcome_text}**", buttons=buttons)
    
    # عند مغادرة/طرد/حظر عضو
    elif (event.user_kicked or event.user_left) and event.user_id and event.user_id != me.id:
        user_id_to_clear = event.user_id
        async with AsyncDBSession() as session:
            # حذف رتب المستخدم من قاعدة البيانات لهذه المجموعة
            await session.execute(delete(Vip).where(Vip.chat_id == event.chat_id, Vip.user_id == user_id_to_clear))
            await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == event.chat_id, BotAdmin.user_id == user_id_to_clear))
            await session.execute(delete(Creator).where(Creator.chat_id == event.chat_id, Creator.user_id == user_id_to_clear))
            await session.execute(delete(SecondaryDev).where(SecondaryDev.chat_id == event.chat_id, SecondaryDev.user_id == user_id_to_clear))
            await session.commit()
            print(f"User {user_id_to_clear} ranks cleared from chat {event.chat_id} due to leaving/being kicked.")

    # عند طرد البوت من المجموعة
    elif (event.user_kicked or event.user_left) and event.user_id == me.id:
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            chat.is_active = False # تعطيل المجموعة
            await session.commit()
        print(f"تمت إزالة البوت من المجموعة {event.chat_id} وتم إيقافه فيها تلقائياً.")

# أمر تفعيل/ايقاف البوت
@client.on(events.NewMessage(pattern="^(تفعيل|ايقاف)$"))
async def toggle_bot_status(event):
    if event.is_private: 
        return
    if not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين يمعود. 😒**")
        
    action = event.raw_text
    me = await client.get_me()
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        
        if action == "ايقاف":
            if not chat.is_active:
                return await event.reply("**أنا معطل أصلاً, شتريد مني بعد 😢**")
            chat.is_active = False
            await session.commit()
            await event.reply("**🔴 خوش، سكتت. لمن تريدني ارجع اشتغل، بس اكتب `تفعيل`.**")
        else:  # تفعيل
            if chat.is_active:
                return await event.reply("**تم تفعيلي سابقا طال عمرك استمتع بالمزايا😎🛠️**")
            
            if not await is_admin(event.chat_id, me.id): 
                return await event.reply("**يمعود ارفعني مشرف أول شي يله اگدر اشتغل! 🤷‍♂️**")
                
            chat.is_active = True
            await session.commit()
            await event.reply("**🟢 رجعتلكم! يلا شنو الأوامر؟**")

@client.on(events.NewMessage(pattern='^الاوامر$'))
async def main_menu_handler(event):
    if event.is_private or not await check_activation(event.chat_id): 
        return
    buttons = await build_main_menu_buttons()
    await event.reply(f"**{MAIN_MENU_MESSAGE}**", buttons=buttons)
