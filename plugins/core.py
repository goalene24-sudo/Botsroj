import asyncio
from telethon import events, Button
from telethon.tl import types
from telethon.tl.types import ChannelParticipantsAdmins
from bot import client
import logging

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from sqlalchemy import delete
from database import AsyncDBSession
from models import Chat, Vip, BotAdmin, Creator, SecondaryDev, User

# --- استيراد الدوال من أماكنها الصحيحة ---
from .utils import (
    check_activation, is_command_enabled, build_main_menu_buttons, 
    MAIN_MENU_MESSAGE, is_admin
)
from .admin import get_or_create_chat, get_chat_setting
# --- (تمت الإضافة هنا) استيراد دالة لوحة الصدارة ---
from .leaderboard import show_leaderboard

logger = logging.getLogger(__name__)
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
            chat_db = await get_or_create_chat(session, chat_id)
            if chat_db:
                chat_db.is_active = False
                await session.commit()
                logger.info(f"Chat {chat_id} created and explicitly set to inactive.")

        try:
            chat = await event.get_chat()
            member_count = (await client.get_participants(chat_id, limit=0)).total
            admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
            admin_count = len(admin_list)
            
            welcome_text = (
                f"**🚨 هلا والله! آني {me.first_name} وصلت حتى احمي المجموعة.**\n\n"
                f"**📊 اسم المجموعة: {chat.title}**\n"
                f"**👥 عددكم: {member_count} نفر**\n"
                f"**🛡️ المشرفين: {admin_count} مدير**\n"
                f"**💻 المطور مالتي: @tit_50**\n\n"
                "**ارفعني مشرف وانطيني الصلاحيات كاملة، ودوس الدگمة الجوه حتى تشوف العجب! 😉**"
            )
            
            activate_button = Button.inline("✅ تفعيل البوت ✅", data=f"activate_{chat_id}")
            await client.send_message(chat_id, welcome_text, buttons=activate_button)
            
        except Exception as e:
            logger.error(f"Failed to send welcome message to {chat_id}: {e}")
        
        await asyncio.sleep(10)
        if chat_id in WELCOMED_RECENTLY:
            WELCOMED_RECENTLY.remove(chat_id)
        return

    # عند ترقية البوت لمشرف (تفعيل تلقائي)
    elif event.user_id == me.id and not (event.user_joined or event.user_left or event.user_kicked):
        try:
            is_bot_now_admin = await is_admin(client, chat_id, me.id)
            is_bot_supposed_to_be_active = await check_activation(chat_id)
            
            if not is_bot_supposed_to_be_active and is_bot_now_admin:
                async with AsyncDBSession() as session:
                    chat = await get_or_create_chat(session, chat_id)
                    if not (chat.settings or {}).get('dev_lock'):
                        chat.is_active = True
                        await session.commit()
                        logger.info(f"Bot was promoted in {chat_id}. Auto-activating.")
                        await client.send_message(chat_id, "**شكراً لترقيتي! ✅ تم تفعيل البوت تلقائياً وجاهز للعمل.**")
        except Exception as e:
            logger.error(f"Error during auto-activation check in {chat_id}: {e}")
        return
    
    # عند طرد البوت من المجموعة
    elif (event.user_kicked or event.user_left) and event.user_id == me.id:
        chat_id = event.chat_id
        logger.info(f"Bot was removed from chat {chat_id}. Deleting all related data.")
        try:
            async with AsyncDBSession() as session:
                await session.execute(delete(User).where(User.chat_id == chat_id))
                await session.execute(delete(Vip).where(Vip.chat_id == chat_id))
                await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == chat_id))
                await session.execute(delete(Creator).where(Creator.chat_id == chat_id))
                await session.execute(delete(SecondaryDev).where(SecondaryDev.chat_id == chat_id))
                await session.execute(delete(Chat).where(Chat.id == chat_id))
                await session.commit()
                logger.info(f"Successfully deleted all data for chat {chat_id}.")
        except Exception as e:
            logger.error(f"Error during data deletion for chat {chat_id}: {e}")
        return

    # عند انضمام عضو جديد
    elif event.user_joined and event.user_id != me.id:
        if not await check_activation(event.chat_id): return
        if not await is_command_enabled(event.chat_id, "welcome_enabled"): return

        chat = await event.get_chat()
        new_user = await event.get_user()
        custom_welcome = await get_chat_setting(event.chat_id, "welcome_message")
        
        if custom_welcome:
            welcome_text = custom_welcome.format(user=f"[{new_user.first_name}](tg://user?id={new_user.id})", group=chat.title)
        else:
            welcome_text = f"**هلا بالضلع الجديد [{new_user.first_name}](tg://user?id={new_user.id}) نورت الكروب يا غالي 🥳**"
        
        buttons = Button.inline("📜 عرض القوانين", data="show_rules")
        await client.send_message(event.chat_id, f"**{welcome_text}**", buttons=buttons)
    
    # عند مغادرة/طرد/حظر عضو
    elif (event.user_kicked or event.user_left) and event.user_id and event.user_id != me.id:
        user_id_to_clear = event.user_id
        async with AsyncDBSession() as session:
            await session.execute(delete(Vip).where(Vip.chat_id == event.chat_id, Vip.user_id == user_id_to_clear))
            await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == event.chat_id, BotAdmin.user_id == user_id_to_clear))
            await session.execute(delete(Creator).where(Creator.chat_id == event.chat_id, Creator.user_id == user_id_to_clear))
            await session.execute(delete(SecondaryDev).where(SecondaryDev.chat_id == event.chat_id, SecondaryDev.user_id == user_id_to_clear))
            await session.commit()

@client.on(events.Raw(types.UpdateChannelParticipant))
async def demotion_handler(update):
    me = await client.get_me()
    
    if update.user_id != me.id:
        return
        
    try:
        chat_id = int(f"-100{update.channel_id}")
        
        if not await check_activation(chat_id):
            return

        prev_role = update.prev_participant
        new_role = update.new_participant

        was_admin = isinstance(prev_role, (types.ChannelParticipantAdmin, types.ChannelParticipantCreator))
        is_now_admin = isinstance(new_role, (types.ChannelParticipantAdmin, types.ChannelParticipantCreator))

        if was_admin and not is_now_admin:
            async with AsyncDBSession() as session:
                chat = await get_or_create_chat(session, chat_id)
                chat.is_active = False
                await session.commit()
            logger.info(f"Bot was demoted in {chat_id} via Raw update. Auto-deactivating.")
            await client.send_message(chat_id, "**⚠️ | تم تنزيلي من الإشراف!**\n**سأتوقف عن العمل هنا حتى يتم ترقيتي وتفعيلي مرة أخرى.**")
    except Exception as e:
        logger.error(f"Error in demotion_handler for chat {update.channel_id}: {e}")

@client.on(events.NewMessage(pattern="^(تفعيل|ايقاف)$"))
async def toggle_bot_status(event):
    if event.is_private: 
        return
    if not await is_admin(client, event.chat_id, event.sender_id):
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
            if (chat.settings or {}).get('dev_lock'):
                return await event.reply("**لا يمكن تفعيل البوت. تم إيقافه من قبل المطور الرئيسي.**")

            if chat.is_active:
                return await event.reply("**تم تفعيلي سابقا طال عمرك استمتع بالمزايا😎🛠️**")
            
            if not await is_admin(client, event.chat_id, me.id): 
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

# --- (تمت الإضافة هنا) معالج أمر لوحة الصدارة ---
@client.on(events.NewMessage(pattern="^(ملوك التفاعل|المتفاعلين)$"))
async def leaderboard_command_handler(event):
    await show_leaderboard(event)
