import asyncio
from datetime import datetime, timedelta
import random
import time
import re
from telethon import events
from telethon.tl.types import MessageEntityUrl, MessageEntityMention, ChannelParticipantsAdmins, ChatBannedRights
from telethon.errors.rpcerrorlist import ChatWriteForbiddenError
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import Alias, MessageHistory, User, Chat

# --- استيراد الأدوات المحدثة ---
from .utils import (
    check_activation,
    FLOOD_TRACKER, get_user_rank, Ranks, get_or_create_chat, get_or_create_user,
    get_global_setting
)
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES
# --- (تم التحديث) استيراد كل الدوال المنطقية الجديدة ---
from .commands_logic import (
    set_rank_logic, 
    my_stats_logic, my_rank_logic, id_logic,
    get_rules_logic, tag_all_logic,
    list_admins_logic
)
from .protection_logic import (
    lock_unlock_logic, kick_logic, unmute_logic,
    set_warns_limit_logic, set_mute_duration_logic,
    ban_logic, unban_logic, mute_logic, warn_logic, clear_warns_logic, timed_mute_logic,
    add_filter_logic, remove_filter_logic, list_filters_logic,
    toggle_id_photo_logic,
    set_rules_logic, clear_rules_logic,
    list_bot_admins_logic, clear_all_bot_admins_logic,
    list_vips_logic, clear_all_vips_logic,
    list_creators_logic, clear_all_creators_logic
)
import logging

logger = logging.getLogger(__name__)

async def handle_flood_lock(event):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        locks = chat.lock_settings or {}
        if not locks.get("flood", False):
            return False
        sender_rank = await get_user_rank(client, event.sender_id, event.chat_id)
        if sender_rank >= Ranks.MOD:
            return False

    user_id, chat_id, now = event.sender_id, event.chat_id, time.time()
    
    if chat_id not in FLOOD_TRACKER: FLOOD_TRACKER[chat_id] = {}
    if user_id not in FLOOD_TRACKER[chat_id]: FLOOD_TRACKER[chat_id][user_id] = []

    FLOOD_TRACKER[chat_id][user_id].append((now, event.text))
    FLOOD_TRACKER[chat_id][user_id] = FLOOD_TRACKER[chat_id][user_id][-5:]
    
    if len(FLOOD_TRACKER[chat_id][user_id]) == 5:
        if (now - FLOOD_TRACKER[chat_id][user_id][0][0]) < 5:
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

async def handle_message_locks(event):
    if event.sender_id in config.SUDO_USERS: return False
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        user = await get_or_create_user(session, event.chat_id, event.sender_id)
        if user.mute_end_time and user.mute_end_time > datetime.now():
            try:
                await event.delete()
            except Exception: pass
            return True
        sender_rank = await get_user_rank(client, event.sender_id, event.chat_id)
        if sender_rank >= Ranks.MOD: return False
        locks, settings = chat.lock_settings or {}, chat.settings or {}
        max_warns, mute_hours = settings.get("max_warns", 3), settings.get("mute_duration_hours", 6)
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
            except Exception as e: logger.warning(f"Failed to delete locked message: {e}")
            user.warns = (user.warns or 0) + 1
            sender = await event.get_sender()
            if user.warns >= max_warns:
                mute_until = datetime.now() + timedelta(hours=mute_hours)
                user.warns, user.mute_end_time = 0, mute_until
                try:
                    await client.edit_permissions(event.chat_id, sender.id, until_date=mute_until, send_messages=False)
                    await event.respond(f"**🚫 | العضو [{sender.first_name}](tg://user?id={sender.id}) وصل للحد الأقصى من التحذيرات (`{max_warns}`).**\n**- تم كتمه تلقائيًا لمدة {mute_hours} ساعات.**")
                except Exception as e:
                    logger.error(f"Failed to mute user {sender.id}: {e}")
                    await event.respond(f"**حاولت اكتم [{sender.first_name}](tg://user?id={sender.id}) بس ماكدرت، يمكن صلاحياتي ناقصة.**")
            else:
                await event.respond(f"**عزيزي [{sender.first_name}](tg://user?id={sender.id})،**\n**{violation_type} ممنوعة هنا بأمر من الإدارة.**\n\n**لقد حصلت على تحذير! ({user.warns}/{max_warns})**")
            await session.commit()
            return True
    return False

@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def general_message_handler(event):
    if not await check_activation(event.chat_id): return
    try:
        if await handle_flood_lock(event) or await handle_message_locks(event): return
        if event.text:
            command_to_process = None
            async with AsyncDBSession() as session:
                result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
                user_aliases = {a.alias_name: a.command_name for a in result.scalars().all()}
            all_aliases = {**FIXED_ALIASES, **user_aliases}
            clean_full_text = re.sub(r"^[!/]", "", event.text.strip())
            command_to_process = all_aliases.get(clean_full_text, clean_full_text)
            disabled_cmds, cmd_parts = await get_global_setting("disabled_cmds", []), command_to_process.split()
            base_cmd = cmd_parts[0] if cmd_parts else ""
            if command_to_process in disabled_cmds or base_cmd in disabled_cmds:
                await event.reply("-هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا اردت شيئا @tit_50-")
                return
            if command_to_process.startswith(("قفل", "فتح")): await lock_unlock_logic(event, command_to_process)
            elif command_to_process.startswith("ضع قوانين"): await set_rules_logic(event, command_to_process)
            elif command_to_process == "مسح القوانين": await clear_rules_logic(event, command_to_process)
            elif command_to_process == "الادمنيه": await list_bot_admins_logic(event, command_to_process)
            elif command_to_process == "مسح كل الادمنيه": await clear_all_bot_admins_logic(event, command_to_process)
            elif command_to_process == "المميزين": await list_vips_logic(event, command_to_process)
            elif command_to_process == "مسح المميزين": await clear_all_vips_logic(event, command_to_process)
            elif command_to_process == "المنشئين": await list_creators_logic(event, command_to_process)
            elif command_to_process == "مسح المنشئين": await clear_all_creators_logic(event, command_to_process)
            elif command_to_process == "طرد": await kick_logic(event, command_to_process)
            elif command_to_process == "الغاء الكتم": await unmute_logic(event, command_to_process)
            elif command_to_process.startswith("ضع عدد التحذيرات"): await set_warns_limit_logic(event, command_to_process)
            elif command_to_process.startswith("ضع وقت الكتم"): await set_mute_duration_logic(event, command_to_process)
            elif command_to_process == "حظر": await ban_logic(event, command_to_process)
            elif command_to_process == "الغاء الحظر": await unban_logic(event, command_to_process)
            elif command_to_process == "كتم" and len(cmd_parts) == 1: await mute_logic(event, command_to_process)
            elif command_to_process.startswith("كتم"): await timed_mute_logic(event, command_to_process)
            elif command_to_process == "تحذير": await warn_logic(event, command_to_process)
            elif command_to_process == "حذف التحذيرات": await clear_warns_logic(event, command_to_process)
            elif command_to_process.startswith("اضف كلمة ممنوعة"): await add_filter_logic(event, command_to_process)
            elif command_to_process.startswith("حذف كلمة ممنوعة"): await remove_filter_logic(event, command_to_process)
            elif command_to_process == "الكلمات الممنوعة": await list_filters_logic(event, command_to_process)
            elif command_to_process in ["تشغيل صورة ايدي", "تعطيل صورة ايدي"]: await toggle_id_photo_logic(event, command_to_process)
            elif command_to_process in ["رفع ادمن", "تنزيل ادمن", "رفع منشئ", "تنزيل منشئ", "رفع مميز", "تنزيل مميز"]: await set_rank_logic(event, command_to_process)
            elif command_to_process == "المدراء": await list_admins_logic(event, command_to_process)
            elif command_to_process == "سجلي": await my_stats_logic(event, command_to_process)
            elif command_to_process == "رتبتي": await my_rank_logic(event, command_to_process)
            elif command_to_process.startswith(("ايدي", "id")): await id_logic(event, command_to_process)
            elif command_to_process == "القوانين": await get_rules_logic(event, command_to_process)
            elif command_to_process.startswith("نداء"): await tag_all_logic(event, command_to_process)
            else:
                async with AsyncDBSession() as session:
                    chat = await get_or_create_chat(session, event.chat_id)
                    user = await get_or_create_user(session, event.chat_id, event.sender_id)
                    user.msg_count = (user.msg_count or 0) + 1
                    chat.total_msgs = (chat.total_msgs or 0) + 1
                    if event.text and (chat.settings or {}).get("public_replies_enabled", True):
                        trigger = event.text.lower()
                        if any(b in trigger for b in ["سروج", "بوت"]):
                            current_rank = await get_user_rank(client, event.sender_id, event.chat_id)
                            chat_settings = chat.settings or {}
                            if current_rank >= Ranks.MAIN_DEV and chat_settings.get("dev_reply"):
                                await event.reply(chat_settings["dev_reply"])
                                return await session.commit()
                            if chat_settings.get("call_reply"):
                                await event.reply(chat_settings["call_reply"])
                                return await session.commit()
                        all_replies = {**DEFAULT_REPLIES, **{k.lower(): v for k, v in (chat.custom_replies or {}).items()}}
                        reply_data = all_replies.get(trigger)
                        if reply_data:
                            reply_template = None
                            if isinstance(reply_data, str): reply_template = reply_data
                            elif isinstance(reply_data, dict):
                                current_rank = await get_user_rank(client, event.sender_id, event.chat_id)
                                if current_rank >= Ranks.MAIN_DEV and "developer" in reply_data: reply_list = reply_data["developer"]
                                elif current_rank >= Ranks.ADMIN and "bot_admin" in reply_data: reply_list = reply_data["bot_admin"]
                                elif current_rank >= Ranks.MOD and "group_admin" in reply_data: reply_list = reply_data["group_admin"]
                                elif "member" in reply_data: reply_list = reply_data["member"]
                                else: reply_list = next((v for v in reply_data.values() if isinstance(v, list)), None)
                                if reply_list: reply_template = random.choice(reply_list)
                            if reply_template:
                                sender = await event.get_sender()
                                try:
                                    await event.reply(reply_template.format(user_mention=f"[{sender.first_name}](tg://user?id={sender.id})", user_first_name=sender.first_name))
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
                    await client.send_message(event.chat_id, welcome_message.format(user=f"[{user_entity.first_name}](tg://user?id={user_entity.id})", group=chat_entity.title))
                await session.commit()
            except Exception as e:
                logger.error(f"خطأ في معالج انضمام الأعضاء: {e}", exc_info=True)
                await session.rollback()

# --- (جديد ومُصحح) دالة إرسال الأذكار الدورية ---
async def start_dhikr_task():
    """تعمل هذه الدالة في الخلفية لإرسال ذكر كل ساعة."""
    while True:
        await asyncio.sleep(3600) # انتظار لمدة ساعة
        try:
            async with AsyncDBSession() as session:
                result = await session.execute(select(Chat).where(Chat.is_active == True))
                active_chats = result.scalars().all()

            if not active_chats:
                logger.info("مهمة الأذكار: لم يتم العثور على مجموعات مفعلة.")
                continue

            dhikr_message = random.choice(DHIKR_LIST)
            
            for chat in active_chats:
                try:
                    await client.send_message(chat.id, f"**{dhikr_message}**")
                    await asyncio.sleep(1) # استراحة بسيطة بين الرسائل
                except ChatWriteForbiddenError:
                    logger.warning(f"مهمة الأذكار: لا يمكن الإرسال إلى المجموعة {chat.id}. قد يكون البوت مطرودًا أو مكتومًا.")
                except Exception as e:
                    logger.error(f"مهمة الأذكار: فشل الإرسال إلى المجموعة {chat.id}: {e}")
        
        except Exception as e:
            logger.error(f"مهمة الأذكار: حدث خطأ في الحلقة الرئيسية: {e}")
