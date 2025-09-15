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
import config
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import Alias, MessageHistory, User
# --- استيراد الأدوات المحدثة ---
from .utils import (
    check_activation,
    FLOOD_TRACKER, get_user_rank, Ranks, get_or_create_chat, get_or_create_user,
    get_global_setting
)
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES
# --- استيراد كل الدوال المنطقية من جميع الملفات ---
from .commands_logic import (
    set_rank_logic, 
    my_stats_logic, my_rank_logic, id_logic,
    get_rules_logic, tag_all_logic,
    list_admins_logic, secondary_dev_logic
)
from .protection_logic import (
    lock_unlock_logic, kick_logic, unmute_logic,
    set_warns_limit_logic, set_mute_duration_logic,
    ban_logic, unban_logic, mute_logic, warn_logic, clear_warns_logic, timed_mute_logic,
    add_filter_logic, remove_filter_logic, list_filters_logic,
    toggle_id_photo_logic
)
from .settings_logic import (
    set_rules_logic, clear_rules_logic,
    set_welcome_logic, clear_welcome_logic,
    list_bot_admins_logic, clear_all_bot_admins_logic,
    list_vips_logic, clear_all_vips_logic,
    list_creators_logic, clear_all_creators_logic,
    promote_demote_logic, set_long_text_size_logic
)
import logging

logger = logging.getLogger(__name__)

# --- دالة منع التكرار ---
async def handle_flood_lock(event):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        locks = chat.lock_settings or {}
        if not locks.get("flood", False):
            return False

    sender_rank = await get_user_rank(event.sender_id, event.chat_id)
    if sender_rank >= Ranks.MOD:
        return False

    user_id = event.sender_id
    chat_id = event.chat_id
    now = time.time()
    
    if chat_id not in FLOOD_TRACKER:
        FLOOD_TRACKER[chat_id] = {}
    if user_id not in FLOOD_TRACKER[chat_id]:
        FLOOD_TRACKER[chat_id][user_id] = []

    FLOOD_TRACKER[chat_id][user_id].append((now, event.text))
    FLOOD_TRACKER[chat_id][user_id] = FLOOD_TRACKER[chat_id][user_id][-5:]
    
    if len(FLOOD_TRACKER[chat_id][user_id]) == 5:
        first_time = FLOOD_TRACKER[chat_id][user_id][0][0]
        if (now - first_time) < 5:
            messages = [msg for _, msg in FLOOD_TRACKER[chat_id][user_id]]
            if len(set(messages)) == 1:
                try:
                    await event.delete()
                    mute_until = datetime.now() + timedelta(minutes=5)
                    await client.edit_permissions(event.chat_id, event.sender_id, until_date=mute_until, send_messages=False)
                    sender = await event.get_sender()
                    await event.respond(f"**🤫 | [{sender.first_name}](tg://user?id={sender.id}) لزكت بالرسالة، اكلت كتم 5 دقايق.**")
                    FLOOD_TRACKER[chat_id][user_id] = []
                    return True
                except Exception as e:
                    logger.warning(f"Failed to handle flood for user {user_id}: {e}")
    return False

# --- دالة الحماية والتحذيرات والكتم ---
async def handle_message_locks(event):
    if event.sender_id in config.SUDO_USERS:
        return False

    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        user = await get_or_create_user(session, event.chat_id, event.sender_id)

        if user.mute_end_time and user.mute_end_time > datetime.now():
            try:
                await event.delete()
            except Exception:
                pass
            return True

        sender_rank = await get_user_rank(event.sender_id, event.chat_id)
        if sender_rank >= Ranks.MOD:
            return False

        locks = chat.lock_settings or {}
        settings = chat.settings or {}
        max_warns = settings.get("max_warns", 3)
        mute_hours = settings.get("mute_duration_hours", 6)
        long_text_size = settings.get("long_text_size", 200)

        violation_type = None
        
        if locks.get("photo") and event.photo: violation_type = "الصور"
        elif locks.get("video") and event.video: violation_type = "الفيديو"
        elif locks.get("sticker") and event.sticker: violation_type = "الملصقات"
        elif locks.get("gif") and event.gif: violation_type = "المتحركات"
        elif locks.get("url") and any(isinstance(e, MessageEntityUrl) for e in (event.entities or [])): violation_type = "الروابط"
        elif locks.get("forward") and event.fwd_from: violation_type = "التوجيه"
        elif locks.get("long_text") and event.text and len(event.text) > long_text_size: violation_type = "الكلايش الطويلة"

        if violation_type:
            try:
                await event.delete()
            except Exception as e:
                logger.warning(f"Failed to delete locked message: {e}")

            user.warns = (user.warns or 0) + 1
            sender = await event.get_sender()
            
            if user.warns >= max_warns:
                mute_until = datetime.now() + timedelta(hours=mute_hours)
                user.warns = 0
                user.mute_end_time = mute_until

                try:
                    await client.edit_permissions(event.chat_id, sender.id, until_date=mute_until, send_messages=False)
                    mute_msg = (f"**🚫 | العضو [{sender.first_name}](tg://user?id={sender.id}) وصل للحد الأقصى من التحذيرات (`{max_warns}`).**\n"
                                f"**- تم كتمه تلقائيًا لمدة {mute_hours} ساعات.**")
                    await event.respond(mute_msg)
                except Exception as e:
                    logger.error(f"Failed to mute user {sender.id}: {e}")
                    await event.respond(f"**حاولت اكتم [{sender.first_name}](tg://user?id={sender.id}) بس ماكدرت، يمكن صلاحياتي ناقصة.**")
            else:
                warn_msg = (f"**عزيزي [{sender.first_name}](tg://user?id={sender.id})،**\n"
                            f"**{violation_type} ممنوعة هنا بأمر من الإدارة.**\n\n"
                            f"**لقد حصلت على تحذير! ({user.warns}/{max_warns})**")
                await event.respond(warn_msg)

            await session.commit()
            return True
    return False


@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def general_message_handler(event):
    if not await check_activation(event.chat_id):
        return
    
    try:
        if await handle_flood_lock(event):
            return
            
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
            
            # --- (تم التحديث) الموزع الجديد والدقيق ---
            
            # --- أوامر الحماية (من protection_logic.py) ---
            if command_to_process.startswith("قفل ") or command_to_process.startswith("فتح "):
                await lock_unlock_logic(event, command_to_process)
            elif command_to_process == "طرد":
                await kick_logic(event, command_to_process)
            elif command_to_process == "الغاء الكتم":
                await unmute_logic(event, command_to_process)
            elif command_to_process.startswith("ضع عدد التحذيرات "):
                await set_warns_limit_logic(event, command_to_process)
            elif command_to_process.startswith("ضع وقت الكتم "):
                await set_mute_duration_logic(event, command_to_process)
            elif command_to_process == "حظر":
                await ban_logic(event, command_to_process)
            elif command_to_process == "الغاء الحظر":
                await unban_logic(event, command_to_process)
            elif command_to_process == "كتم":
                await mute_logic(event, command_to_process)
            elif re.match(r"^كتم \d+ [ديس]$", command_to_process):
                await timed_mute_logic(event, command_to_process)
            elif command_to_process == "تحذير":
                await warn_logic(event, command_to_process)
            elif command_to_process == "حذف التحذيرات":
                await clear_warns_logic(event, command_to_process)
            elif command_to_process.startswith("اضف كلمة ممنوعة "):
                await add_filter_logic(event, command_to_process)
            elif command_to_process.startswith("حذف كلمة ممنوعة "):
                await remove_filter_logic(event, command_to_process)
            elif command_to_process == "الكلمات الممنوعة":
                await list_filters_logic(event, command_to_process)
            
            # --- أوامر الإعدادات (من settings_logic.py) ---
            elif command_to_process.startswith("ضع قوانين "):
                await set_rules_logic(event, command_to_process)
            elif command_to_process == "مسح القوانين":
                await clear_rules_logic(event, command_to_process)
            elif command_to_process.startswith("ضع ترحيب "):
                await set_welcome_logic(event, command_to_process)
            elif command_to_process == "حذف الترحيب":
                await clear_welcome_logic(event, command_to_process)
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
            elif command_to_process.startswith("ضع حجم الكلايش "):
                await set_long_text_size_logic(event, command_to_process)
            elif command_to_process in ["تشغيل صورة ايدي", "تعطيل صورة ايدي"]:
                await toggle_id_photo_logic(event, command_to_process)

            # --- أوامر الرتب والملف الشخصي (من commands_logic.py) ---
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
            elif command_to_process == "ايدي" or command_to_process.startswith("ايدي "):
                await id_logic(event, command_to_process)
            elif command_to_process == "id" or command_to_process.startswith("id "):
                await id_logic(event, command_to_process)
            elif command_to_process == "القوانين":
                await get_rules_logic(event, command_to_process)
            elif command_to_process == "نداء" or command_to_process.startswith("نداء "):
                await tag_all_logic(event, command_to_process)
            
            # --- منطق الرسائل العادية (غير الأوامر) ---
            else:
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
