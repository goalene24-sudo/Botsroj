import asyncio
from datetime import datetime, timedelta
import random
import time
import re
from telethon import events
from telethon.tl.types import MessageEntityUrl, MessageEntityMention, ChannelParticipantsAdmins, ChatBannedRights
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config # <-- (تمت إضافة هذا السطر لإصلاح الخطأ)
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import Alias, MessageHistory, User
# --- استيراد الأدوات المحدثة ---
from .utils import (
    check_activation, PERCENT_COMMANDS, GAME_COMMANDS, ADMIN_COMMANDS,
    FLOOD_TRACKER, get_user_rank, Ranks, get_or_create_chat, get_or_create_user,
    get_global_setting
)
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES
# --- استيراد منطق الأوامر الجديد ---
from .commands_logic import (
    lock_unlock_logic, kick_logic, set_rank_logic, 
    my_stats_logic, my_rank_logic, id_logic,
    get_rules_logic, toggle_id_photo_logic, tag_all_logic,
    set_warns_limit_logic, set_mute_duration_logic, unmute_logic
)
import logging

logger = logging.getLogger(__name__)

# --- دالة لمعالجة قفل الرسائل والتحذيرات والكتم ---
async def handle_message_locks(event):
    # لا نطبق النظام على المطورين
    if event.sender_id in config.SUDO_USERS:
        return False

    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        user = await get_or_create_user(session, event.chat_id, event.sender_id)

        # التحقق إذا كان المستخدم مكتومًا بالفعل من خلال البوت
        if user.mute_end_time and user.mute_end_time > datetime.now():
            try:
                await event.delete()
            except Exception:
                pass
            return True # نمنع المستخدم المكتوم من إرسال أي شيء

        sender_rank = await get_user_rank(event.sender_id, event.chat_id)
        if sender_rank >= Ranks.MOD: # استثناء المشرفين فما فوق
            return False

        locks = chat.lock_settings or {}
        settings = chat.settings or {}
        max_warns = settings.get("max_warns", 3)
        mute_hours = settings.get("mute_duration_hours", 6)
        
        violation_type = None
        
        if locks.get("photo") and event.photo: violation_type = "الصور"
        elif locks.get("video") and event.video: violation_type = "الفيديو"
        elif locks.get("sticker") and event.sticker: violation_type = "الملصقات"
        elif locks.get("gif") and event.gif: violation_type = "المتحركات"
        elif locks.get("url") and any(isinstance(e, MessageEntityUrl) for e in (event.entities or [])): violation_type = "الروابط"
        elif locks.get("forward") and event.fwd_from: violation_type = "التوجيه"
        elif locks.get("long_text") and event.text and len(event.text) > 200: violation_type = "الكلايش الطويلة"

        if violation_type:
            try:
                await event.delete()
            except Exception as e:
                logger.warning(f"Failed to delete locked message: {e}")

            user.warns = (user.warns or 0) + 1
            sender = await event.get_sender()
            
            # التحقق إذا وصل للحد الأقصى
            if user.warns >= max_warns:
                mute_until = datetime.now() + timedelta(hours=mute_hours)
                user.warns = 0 # تصفير التحذيرات
                user.mute_end_time = mute_until

                try:
                    await client.edit_permissions(
                        event.chat_id, 
                        sender.id, 
                        until_date=mute_until, 
                        send_messages=False
                    )
                    mute_msg = (
                        f"**🚫 | العضو [{sender.first_name}](tg://user?id={sender.id}) وصل للحد الأقصى من التحذيرات (`{max_warns}`).**\n"
                        f"**- تم كتمه تلقائيًا لمدة {mute_hours} ساعات.**"
                    )
                    await event.respond(mute_msg)
                except Exception as e:
                    logger.error(f"Failed to mute user {sender.id}: {e}")
                    await event.respond(f"**حاولت اكتم [{sender.first_name}](tg://user?id={sender.id}) بس ماكدرت، يمكن صلاحياتي ناقصة.**")
            else:
                warn_msg = (
                    f"**عزيزي [{sender.first_name}](tg://user?id={sender.id})،**\n"
                    f"**{violation_type} ممنوعة هنا بأمر من الإدارة.**\n\n"
                    f"**لقد حصلت على تحذير! ({user.warns}/{max_warns})**"
                )
                await event.respond(warn_msg)

            await session.commit()
            return True

    return False


@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def general_message_handler(event):
    if not await check_activation(event.chat_id):
        return
    
    # وضعنا كتلة try...except شاملة هنا لالتقاط أي خطأ غير متوقع
    try:
        if await handle_message_locks(event):
            return

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
            
            # --- توجيه الأوامر ---
            if command_to_process.startswith("ضع عدد التحذيرات"):
                await set_warns_limit_logic(event, command_to_process)
                return
            elif command_to_process.startswith("ضع وقت الكتم"):
                await set_mute_duration_logic(event, command_to_process)
                return
            elif command_to_process.startswith("الغاء الكتم"):
                await unmute_logic(event, command_to_process)
                return
            elif command_to_process.startswith(("قفل", "فتح")):
                await lock_unlock_logic(event, command_to_process)
                return
            elif command_to_process == "طرد":
                await kick_logic(event, command_to_process)
                return
            elif command_to_process in ["رفع ادمن", "تنزيل ادمن", "رفع منشئ", "تنزيل منشئ", "رفع مميز", "تنزيل مميز"]:
                await set_rank_logic(event, command_to_process)
                return
            elif command_to_process == "سجلي":
                await my_stats_logic(event, command_to_process)
                return
            elif command_to_process == "رتبتي":
                await my_rank_logic(event, command_to_process)
                return
            elif command_to_process.startswith("ايدي") or command_to_process.startswith("id"):
                await id_logic(event, command_to_process)
                return
            elif command_to_process == "القوانين":
                await get_rules_logic(event, command_to_process)
                return
            elif command_to_process.startswith("نداء"):
                await tag_all_logic(event, command_to_process)
                return
            elif command_to_process in ["تشغيل صورة ايدي", "تعطيل صورة ايدي"]:
                await toggle_id_photo_logic(event, command_to_process)
                return

        # --- منطق الرسائل العادية (غير الأوامر) ---
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            user = await get_or_create_user(session, event.chat_id, event.sender_id)

            user.msg_count = (user.msg_count or 0) + 1
            chat.total_msgs = (chat.total_msgs or 0) + 1
            
            if event.text and (chat.settings or {}).get("public_replies_enabled", True):
                trigger = event.text.lower()
                
                BOT_TRIGGERS = ["سروج", "بوت"]
                if any(b in trigger for b in BOT_TRIGGERS):
                    current_rank = await get_user_rank(event.sender_id, event.chat_id)
                    chat_settings = chat.settings or {}
                    if current_rank >= Ranks.MAIN_DEV and chat_settings.get("dev_reply"):
                        await event.reply(chat_settings["dev_reply"])
                        await session.commit()
                        return
                    if chat_settings.get("call_reply"):
                        await event.reply(chat_settings["call_reply"])
                        await session.commit()
                        return
                
                all_replies = DEFAULT_REPLIES.copy()
                custom_replies = chat.custom_replies or {}
                all_replies.update({k.lower(): v for k, v in custom_replies.items()})
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


@client.on(events.ChatAction)
async def handle_chat_action(event):
    if event.user_joined or event.user_added:
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
