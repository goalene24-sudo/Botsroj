import asyncio
from datetime import datetime, timedelta
import random
import time
import re
from telethon import events
from telethon.tl.types import MessageEntityUrl, MessageEntityMention
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import Alias, MessageHistory

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
    get_rules_logic, toggle_id_photo_logic, tag_all_logic
)
import logging

# إعداد السجل
logger = logging.getLogger(__name__)


@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def general_message_handler(event):
    if not await check_activation(event.chat_id):
        return

    try:
        # --- (النسخة النهائية) محرك ترجمة وتوجيه الأوامر ---
        if event.text:
            command_to_process = None
            async with AsyncDBSession() as session:
                result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
                aliases_from_db = result.scalars().all()
                user_aliases = {a.alias_name: a.command_name for a in aliases_from_db}
            
            all_aliases = FIXED_ALIASES.copy()
            all_aliases.update(user_aliases)

            full_text = event.text.strip()
            # إزالة العلامات مثل ! أو / من بداية الأمر لتطابق القائمة المعطلة
            clean_full_text = re.sub(r"^[!/]", "", full_text)
            
            translated_command = all_aliases.get(clean_full_text)
            
            command_to_process = translated_command if translated_command is not None else clean_full_text

            # --- التحقق من الأوامر المعطلة عالميًا ---
            disabled_cmds = await get_global_setting("disabled_cmds", [])
            cmd_parts = command_to_process.split()
            base_cmd = cmd_parts[0] if cmd_parts else ""

            if command_to_process in disabled_cmds or base_cmd in disabled_cmds:
                # --- (تم التعديل) إضافة رد بدلاً من التجاهل الصامت ---
                await event.reply("-هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا اردت شيئا @tit_50-")
                return  # إيقاف تنفيذ الأمر بعد الرد
            # --- نهاية التعديل ---

            if command_to_process.startswith(("قفل", "فتح")):
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
            
            # --- نظام الردود (تمت إعادة بناء المنطق بالكامل) ---
            if event.text and (chat.settings or {}).get("public_replies_enabled", True):
                trigger = event.text.lower()
                
                # الخطوة 1: التحقق من ردود المناداة الخاصة أولاً
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
                
                # الخطوة 2: إذا لم يتم إرسال رد خاص، تحقق من الردود العامة
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
