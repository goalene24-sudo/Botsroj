import asyncio
import logging
from datetime import datetime
from telethon import events, Button
from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantCreator

from bot import client
from database import AsyncDBSession
from sqlalchemy.future import select
from sqlalchemy import delete
from models import Chat, User, Vip, BotAdmin, Creator, SecondaryDev, Alias
from .utils import KICKED_CHATS, get_or_create_chat, check_activation, get_chat_setting, get_or_create_user

logger = logging.getLogger(__name__)

# --- دالة التفعيل الموحدة (للنص والزر) ---
async def perform_activation(event):
    try:
        user_id = event.sender_id
        chat_id = event.chat_id

        # التحقق من أن المستخدم مشرف
        try:
            participant = await client.get_participant(chat_id, user_id)
            if not (participant.admin_rights or isinstance(participant.participant, ChannelParticipantCreator)):
                msg = "**عذرًا، فقط مشرفي المجموعة يمكنهم تفعيل البوت.**"
                return await event.answer(msg, alert=True) if hasattr(event, 'answer') else await event.reply(msg)
        except Exception:
            msg = "**لا أستطيع رؤية صلاحياتك، هل أنت متأكد من أنك عضو في المجموعة؟**"
            return await event.answer(msg, alert=True) if hasattr(event, 'answer') else await event.reply(msg)

        # التحقق من أن البوت مشرف
        try:
            me = await client.get_me()
            bot_participant = await client.get_participant(chat_id, me.id)
            if not bot_participant.admin_rights:
                msg = "**⚠️ | لست مشرفًا في المجموعة! يرجى رفعي كمشرف أولاً ثم حاول مجددًا.**"
                return await event.answer(msg, alert=True) if hasattr(event, 'answer') else await event.reply(msg)
        except Exception:
             msg = "**⚠️ | لا أستطيع التحقق من صلاحياتي. يرجى رفعي كمشرف أولاً.**"
             return await event.answer(msg, alert=True) if hasattr(event, 'answer') else await event.reply(msg)

        KICKED_CHATS.discard(chat_id)

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, chat_id)
            if chat.is_active:
                msg = "**✅ | البوت مفعل بالفعل في هذه المجموعة!**"
                return await event.answer(msg, alert=True) if hasattr(event, 'answer') else await event.reply(msg)
            
            chat.is_active = True
            await session.commit()
        
        msg = "**✅ | تم تفعيل البوت بنجاح في هذه المجموعة.**\n**- أرسل `الاوامر` لعرض قائمة الأوامر.**"
        if hasattr(event, 'edit'):
            await event.edit(msg)
        else:
            await event.reply(msg)
            
    except Exception as e:
        logger.error(f"Error in activation logic: {e}", exc_info=True)
        if hasattr(event, 'answer'):
            await event.answer("حدث خطأ أثناء التفعيل. 😢", alert=True)
        else:
            await event.reply("**حدث خطأ أثناء محاولة تفعيل البوت. 😢**")

# --- معالج أحداث المجموعة (إضافة/طرد/انضمام) ---
@client.on(events.ChatAction)
async def core_chat_action_handler(event):
    me = await client.get_me()

    # 1. عند إضافة البوت لمجموعة جديدة
    if event.user_added and event.user_id == me.id:
        chat_id = event.chat_id
        logger.info(f"Bot added to new group: {chat_id}")

        async with AsyncDBSession() as session:
            chat_db = await get_or_create_chat(session, chat_id)
            if chat_db:
                chat_db.is_active = False
                await session.commit()
        
        KICKED_CHATS.discard(chat_id)

        try:
            chat_info = await event.get_chat()
            member_count = (await client.get_participants(chat_id, limit=0)).total
            admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
            admin_count = len(admin_list)
            
            welcome_text = (
                f"**🚨 هلا والله! آني {me.first_name} وصلت حتى احمي المجموعة.**\n\n"
                f"**📊 اسم المجموعة: {chat_info.title}**\n"
                f"**👥 عددكم: {member_count} نفر**\n"
                f"**🛡️ المشرفين: {admin_count} مدير**\n"
                f"**💻 المطور مالتي: @tit_50**\n\n"
                "**ارفعني مشرف وانطيني الصلاحيات كاملة، ودوس الدگمة الجوه حتى تشوف العجب! 😉**"
            )
            
            activate_button = Button.inline("✅ تفعيل البوت ✅", data="core_activate")
            await client.send_message(chat_id, welcome_text, buttons=activate_button)
        except Exception as e:
            logger.error(f"Failed to send welcome message to {chat_id}: {e}")
        return

    # 2. عند طرد البوت من المجموعة
    if (event.user_left or event.user_kicked) and event.user_id == me.id:
        chat_id = event.chat_id
        KICKED_CHATS.add(chat_id)
        logger.info(f"Bot was removed from chat {chat_id}. Deleting all related data.")
        try:
            async with AsyncDBSession() as session:
                await session.execute(delete(User).where(User.chat_id == chat_id))
                await session.execute(delete(Alias).where(Alias.chat_id == chat_id))
                await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == chat_id))
                await session.execute(delete(Creator).where(Creator.chat_id == chat_id))
                await session.execute(delete(Vip).where(Vip.chat_id == chat_id))
                await session.execute(delete(SecondaryDev).where(SecondaryDev.chat_id == chat_id))
                await session.execute(delete(Chat).where(Chat.id == chat_id))
                await session.commit()
                logger.info(f"Successfully deleted all data for chat {chat_id}.")
        except Exception as e:
            logger.error(f"Failed to delete data for chat {chat_id}: {e}", exc_info=True)
        return

    # 3. عند انضمام عضو جديد للمجموعة
    if event.user_joined and event.user_id != me.id:
        if not await check_activation(event.chat_id): return
        
        custom_welcome = await get_chat_setting(event.chat_id, "welcome_message")
        if custom_welcome:
            try:
                user_entity = await event.get_user()
                chat_entity = await event.get_chat()
                formatted_message = custom_welcome.format(user=f"[{user_entity.first_name}](tg://user?id={user_entity.id})", group=chat_entity.title)
                await client.send_message(event.chat_id, formatted_message)
            except Exception as e:
                logger.error(f"Error in custom welcome: {e}")

# --- معالج زر التفعيل ---
@client.on(events.CallbackQuery(pattern=b"core_activate"))
async def handle_core_activation_button(event):
    await perform_activation(event)

# --- معالج أوامر تفعيل/ايقاف النصية ---
@client.on(events.NewMessage(pattern=r"^[!/](تفعيل|ايقاف)$"))
async def toggle_bot_status_handler(event):
    if event.raw_text.strip() in ["تفعيل", "/تفعيل", "!تفعيل"]:
        await perform_activation(event)
    else: # إيقاف
        if not await check_activation(event.chat_id):
            return
        try:
            participant = await client.get_participant(event.chat_id, event.sender_id)
            if not (participant.admin_rights or isinstance(participant.participant, ChannelParticipantCreator)):
                return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين يمعود. 😒**")

            async with AsyncDBSession() as session:
                chat = await get_or_create_chat(session, event.chat_id)
                if not chat.is_active:
                    return await event.reply("**أنا معطل أصلاً, شتريد مني بعد 😢**")
                
                chat.is_active = False
                await session.commit()
            
            await event.reply("**🔴 خوش، سكتت. لمن تريدني ارجع اشتغل، بس اكتب `تفعيل`.**")
        except Exception as e:
            logger.error(f"Error in deactivation: {e}")
