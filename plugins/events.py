import asyncio
from datetime import datetime, timedelta
import random
import time
import re
from telethon import events, Button
from telethon.tl.types import MessageEntityUrl, MessageEntityMention, ChannelParticipantsAdmins, ChatBannedRights
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
# --- استيراد المكونات وقواعد البيانات ---
from database import AsyncDBSession
from models import Alias, User, Chat, BotAdmin, Creator, Vip, SecondaryDev
# --- استيراد الأدوات المحدثة وكل ما يلزم ---
from .utils import (
    check_activation,
    KICKED_CHATS,
    FLOOD_TRACKER, get_user_rank, Ranks, get_or_create_chat, get_or_create_user,
    get_global_setting
)
from .default_replies import DEFAULT_REPLIES
# --- استيراد الدوال المنطقية المتبقية ---
from .commands_logic import (
    set_rank_logic, 
    my_stats_logic, my_rank_logic, id_logic,
    get_rules_logic, tag_all_logic,
    list_admins_logic, secondary_dev_logic
)
from .settings_logic import (
    activation_logic, deactivation_logic,
    set_rules_logic, clear_rules_logic,
    set_welcome_logic, clear_welcome_logic,
    pin_logic, unpin_logic,
    list_bot_admins_logic, clear_all_bot_admins_logic,
    list_vips_logic, clear_all_vips_logic,
    list_creators_logic, clear_all_creators_logic,
    promote_demote_logic, set_long_text_size_logic
)
import logging

logger = logging.getLogger(__name__)


# --- (موحد) معالج أحداث المجموعة (إضافة/مغادرة/انضمام) ---
@client.on(events.ChatAction)
async def handle_chat_action(event):
    me = await client.get_me()

    # --- 1. عند إضافة البوت إلى مجموعة جديدة ---
    if event.user_added and event.user_id == me.id:
        chat_id = event.chat_id
        logger.info(f"Bot added to new group: {chat_id}")

        async with AsyncDBSession() as session:
            chat_db = await get_or_create_chat(session, chat_id)
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
            
            activate_button = Button.inline("✅ تفعيل البوت ✅", data="activate")
            await client.send_message(chat_id, welcome_text, buttons=activate_button)
        except Exception as e:
            logger.error(f"Failed to send welcome message to {chat_id}: {e}")
        return

    # --- 2. عند طرد البوت من المجموعة ---
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

    # --- 3. عند انضمام عضو جديد (وليس البوت) ---
    if event.user_joined and event.user_id != me.id:
        if not await check_activation(event.chat_id): return
        async with AsyncDBSession() as session:
            try:
                user = await get_or_create_user(session, event.chat_id, event.user_id)
                user.join_date = datetime.now().strftime("%Y-%m-%d")
                chat = await get_or_create_chat(session, event.chat_id)
                welcome_message = (chat.settings or {}).get("welcome_message")
                if welcome_message:
                    user_entity = await event.get_user()
                    chat_entity = await event.get_chat()
                    formatted_message = welcome_message.format(user=f"[{user_entity.first_name}](tg://user?id={user_entity.id})", group=chat_entity.title)
                    await client.send_message(event.chat_id, formatted_message)
                await session.commit()
            except Exception as e:
                logger.error(f"خطأ في معالج انضمام الأعضاء: {e}", exc_info=True)
                await session.rollback()

# --- معالج زر التفعيل ---
@client.on(events.CallbackQuery(pattern=b"activate"))
async def handle_activation_button(event):
    await event.answer("جاري محاولة التفعيل...", alert=False)
    await activation_logic(event)


# --- معالج الرسائل والأوامر الرئيسي ---
@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def general_message_handler(event):
    is_activation_cmd = False
    if event.text:
        clean_text = re.sub(r"^[!/]", "", event.text.strip())
        if clean_text in ["تفعيل", "activate"]:
            is_activation_cmd = True
    
    if not is_activation_cmd:
        if not await check_activation(event.chat_id):
            return
    
    try:
        if await handle_flood_lock(event): return
        if await handle_message_locks(event): return

        if event.text:
            command_to_process = None
            async with AsyncDBSession() as session:
                result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
                aliases_from_db = result.scalars().all()
                user_aliases = {a.alias_name: a.command_name for a in aliases_from_db}
            
            all_aliases = FIXED_ALIASES.copy()
            all_aliases.update(user_aliases)

            full_text = event.text.strip()
            clean_full_text = re.sub(r"^[!/]", "", full_text)
            
            translated_command = all_aliases.get(clean_full_text)
            command_to_process = translated_command if translated_command is not None else clean_full_text

            disabled_cmds = await get_global_setting("disabled_cmds", [])
            cmd_parts = command_to_process.split()
            base_cmd = cmd_parts[0] if cmd_parts else ""

            if command_to_process in disabled_cmds or base_cmd in disabled_cmds:
                await event.reply("-هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا اردت شيئا @tit_50-")
                return
            
            # --- الموزع الموحد والمنظم ---
            if base_cmd in ["تفعيل", "activate"]:
                await activation_logic(event, command_to_process)
            elif base_cmd == "ايقاف":
                await deactivation_logic(event, command_to_process)
            elif base_cmd in ["ايدي", "id"]:
                await id_logic(event, command_to_process)
            elif command_to_process.startswith("ضع قوانين"):
                await set_rules_logic(event, command_to_process)
            elif command_to_process == "مسح القوانين":
                await clear_rules_logic(event, command_to_process)
            elif command_to_process.startswith("ضع ترحيب"):
                await set_welcome_logic(event, command_to_process)
            elif command_to_process == "حذف الترحيب":
                await clear_welcome_logic(event, command_to_process)
            elif command_to_process == "تثبيت":
                await pin_logic(event, command_to_process)
            elif command_to_process == "الغاء التثبيت":
                await unpin_logic(event, command_to_process)
            elif command_to_process == "الادمنيه":
                await list_bot_admins_logic(event, command_to_process)
            elif command_to_process == "مسح كل الادمنيه":
                await clear_all_bot_admins_logic(event, command_to_process)
            elif command_to_process == "المميزين":
                await list_vips_logic(event, command_to_process)
            elif command_to_process == "مسح المميزين":
                await clear_all_vips_logic(event, command_to_process)
            elif command_to_process == "المنشئين":
                await list_creators_logic(event, command_to_process)
            elif command_to_process == "مسح المنشئين":
                await clear_all_creators_logic(event, command_to_process)
            elif command_to_process in ["رفع مشرف", "تنزيل مشرف"]:
                await promote_demote_logic(event, command_to_process)
            elif command_to_process.startswith("ضع حجم الكلايش"):
                await set_long_text_size_logic(event, command_to_process)
            elif command_to_process in ["رفع ادمن", "تنزيل ادمن", "رفع منشئ", "تنزيل منشئ", "رفع مميز", "تنزيل مميز"]:
                await set_rank_logic(event, command_to_process)
            elif command_to_process in ["رفع مطور ثانوي", "تنزيل مطور ثانوي", "المطورين الثانويين", "مسح المطورين الثانويين"]:
                await secondary_dev_logic(event, command_to_process)
            elif command_to_process == "المدراء":
                await list_admins_logic(event, command_to_process)
            elif command_to_process == "سجلي":
                await my_stats_logic(event, command_to_process)
            elif command_to_process == "رتبتي":
                await my_rank_logic(event, command_to_process)
            elif command_to_process == "القوانين":
                await get_rules_logic(event, command_to_process)
            elif base_cmd == "نداء":
                await tag_all_logic(event, command_to_process)
            else:
                async with AsyncDBSession() as session:
                    chat = await get_or_create_chat(session, event.chat_id)
                    user = await get_or_create_user(session, event.chat_id, event.sender_id)
                    user.msg_count = (user.msg_count or 0) + 1
                    chat.total_msgs = (chat.total_msgs or 0) + 1
                    
                    if event.text and (chat.settings or {}).get("public_replies_enabled", True):
                        trigger = event.text.lower()
                        all_replies = DEFAULT_REPLIES.copy()
                        custom_replies = (chat.custom_replies or {})
                        all_replies.update({k.lower(): v for k,v in custom_replies.items()})
                        reply_data = all_replies.get(trigger)
                        if reply_data:
                            reply_template = None
                            if isinstance(reply_data, str):
                                reply_template = reply_data
                            elif isinstance(reply_data, dict):
                                current_rank = await get_user_rank(event.sender_id, event.chat_id)
                                if current_rank >= Ranks.MAIN_DEV and "developer" in reply_data: reply_list = reply_data["developer"]
                                elif current_rank >= Ranks.ADMIN and "bot_admin" in reply_data: reply_list = reply_data["bot_admin"]
                                elif current_rank >= Ranks.MOD and "group_admin" in reply_data: reply_list = reply_data["group_admin"]
                                elif "member" in reply_data: reply_list = reply_data["member"]
                                else: reply_list = next((v for v in reply_data.values() if isinstance(v, list)), None)
                                if reply_list: reply_template = random.choice(reply_list)
                            
                            if reply_template:
                                sender = await event.get_sender()
                                try:
                                    final_reply = reply_template.format(user_mention=f"[{sender.first_name}](tg://user?id={sender.id})", user_first_name=sender.first_name)
                                    await event.reply(final_reply)
                                except KeyError:
                                    await event.reply(reply_template)
                    await session.commit()
    except Exception as e:
        logger.error(f"استثناء غير معالج في general_message_handler: {e}", exc_info=True)
