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
    FLOOD_TRACKER, get_user_rank, Ranks, get_or_create_chat, get_or_create_user
)
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES
# --- استيراد منطق الأوامر الجديد ---
from .commands_logic import lock_unlock_logic
import logging

# إعداد السجل
logger = logging.getLogger(__name__)

@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def general_message_handler(event):
    if not await check_activation(event.chat_id):
        return

    async with AsyncDBSession() as session:
        try:
            # --- محرك ترجمة الأوامر والموزع الرئيسي ---
            if event.text:
                result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
                aliases_from_db = result.scalars().all()
                user_aliases = {a.alias_name: a.command_name for a in aliases_from_db}
                
                all_aliases = FIXED_ALIASES.copy()
                all_aliases.update(user_aliases)

                full_text = event.text.strip()
                original_command = None

                if full_text in all_aliases:
                    original_command = all_aliases[full_text]
                else:
                    message_parts = full_text.split()
                    if message_parts:
                        command_candidate = message_parts[0]
                        if command_candidate in all_aliases:
                            translated_first_word = all_aliases[command_candidate]
                            new_message_parts = [translated_first_word] + message_parts[1:]
                            original_command = " ".join(new_message_parts)

                # إذا تم العثور على ترجمة، قم بتوجيهها للمنطق المناسب
                if original_command:
                    # تحديث نص الرسالة في الحدث لكي يستخدمه المنطق
                    event.message.message = original_command
                    
                    # --- الموزع (Router) ---
                    # 1. التحقق من أووامر القفل والفتح
                    if original_command.startswith(("قفل", "فتح")):
                        # --- رسالة تشخيصية ---
                        logger.info(f"[ROUTER] Command '{original_command}' matched. Calling lock_unlock_logic.")
                        await lock_unlock_logic(event)
                        logger.info(f"[ROUTER] lock_unlock_logic finished.")
                        raise events.StopPropagation # إيقاف المعالجة لأن الأمر تم تنفيذه
                    
            # --- جلب كائنات المجموعة والمستخدم (فقط إذا لم يكن أمراً) ---
            chat = await get_or_create_chat(session, event.chat_id)
            user = await get_or_create_user(session, event.chat_id, event.sender_id)
            
            # --- نظام تخزين الرسائل مع الأنواع ---
            if event.id:
                long_text_size = (chat.settings or {}).get("long_text_size", 200)
                msg_type = "text"
                message_entities = event.message.entities or []
                
                if event.photo: msg_type = "photo"
                elif event.video: msg_type = "video"
                elif event.sticker: msg_type = "sticker"
                elif event.gif: msg_type = "gif"
                elif event.document: msg_type = "document"
                elif event.text and len(event.text) > long_text_size: msg_type = "long_text"
                elif any(isinstance(e, MessageEntityUrl) for e in message_entities): msg_type = "url"
                elif event.forward: msg_type = "forward"

                new_msg = MessageHistory(chat_id=event.chat_id, msg_id=event.id, msg_type=msg_type)
                session.add(new_msg)
                
                history_count = (await session.execute(
                    select(func.count(MessageHistory.id)).where(MessageHistory.chat_id == event.chat_id)
                )).scalar_one()

                if history_count > 100:
                    oldest_msg_id_res = await session.execute(
                        select(MessageHistory.id).where(MessageHistory.chat_id == event.chat_id).order_by(MessageHistory.id.asc()).limit(1)
                    )
                    oldest_msg_id = oldest_msg_id_res.scalar_one_or_none()
                    if oldest_msg_id:
                        await session.execute(delete(MessageHistory).where(MessageHistory.id == oldest_msg_id))

            # --- ميزة الذكر التلقائي ---
            now = int(time.time())
            chat_settings = chat.settings or {}
            last_dhikr_time = chat_settings.get("last_dhikr_time", 0)
            dhikr_interval = chat_settings.get("dhikr_interval", 3600)
            is_dhikr_enabled = chat_settings.get("dhikr_enabled", True)

            if is_dhikr_enabled and (now - last_dhikr_time > dhikr_interval):
                dhikr_message = random.choice(DHIKR_LIST)
                await client.send_message(event.chat_id, dhikr_message)
                chat_settings["last_dhikr_time"] = now
                chat.settings = chat_settings
                flag_modified(chat, "settings")

            # --- فحص الرتب والأقفال ---
            rank_int = await get_user_rank(event.sender_id, event.chat_id)
            is_immune = rank_int >= Ranks.MOD

            if not is_immune:
                chat_locks = chat.lock_settings or {}
                message_entities_for_lock = event.message.entities or []
                checks = {
                    "photo": event.photo, "video": event.video, "gif": event.gif,
                    "sticker": event.sticker, "url": any(isinstance(e, MessageEntityUrl) for e in message_entities_for_lock),
                    "username": any(isinstance(e, MessageEntityMention) for e in message_entities_for_lock),
                    "forward": event.forward, "bot": event.via_bot
                }
                for lock_name, condition in checks.items():
                    if chat_locks.get(lock_name) and condition:
                        try:
                            await event.delete()
                        except Exception: pass
                        return

                # --- نظام التكرار ---
                if chat_locks.get("anti_flood", False):
                    user_id = event.sender_id
                    chat_id = event.chat_id
                    now = time.time()
                    
                    if chat_id not in FLOOD_TRACKER: FLOOD_TRACKER[chat_id] = {}
                    if user_id not in FLOOD_TRACKER[chat_id]: FLOOD_TRACKER[chat_id][user_id] = []
                    
                    FLOOD_TRACKER[chat_id][user_id].append(now)
                    FLOOD_TRACKER[chat_id][user_id] = [t for t in FLOOD_TRACKER[chat_id][user_id] if now - t < 3]
                    
                    if len(FLOOD_TRACKER[chat_id][user_id]) >= 5:
                        try:
                            until_date = datetime.now() + timedelta(minutes=5)
                            await client.edit_permissions(chat_id, user_id, send_messages=False, until_date=until_date)
                            await event.reply(f"**تم كتم [{event.sender.first_name}](tg://user?id={user_id}) لمدة 5 دقائق بسبب التكرار.**")
                            FLOOD_TRACKER[chat_id][user_id] = []
                        except Exception: pass
                        return

                # --- نظام الكلمات الممنوعة ---
                if event.text:
                    filtered_words = (chat.settings or {}).get("filtered_words", [])
                    if filtered_words and any(word.lower() in event.text.lower() for word in filtered_words):
                        try:
                            await event.delete()
                            sender = await event.get_sender()
                            user.warns = (user.warns or 0) + 1
                            max_warns = (chat.settings or {}).get("max_warns", 3)
                            if user.warns >= max_warns:
                                until_date = datetime.now() + timedelta(days=1)
                                await client.edit_permissions(event.chat_id, sender.id, send_messages=False, until_date=until_date)
                                await client.send_message(event.chat_id, f"**❗️تم كتم [{sender.first_name}](tg://user?id={sender.id}) لمدة 24 ساعة** لتجاوز التحذيرات.")
                                user.warns = 0
                            else:
                                await client.send_message(event.chat_id, f"**⚠️ تم حذف رسالة من [{sender.first_name}](tg://user?id={sender.id}) لمخالفة القوانين.\nعدد تحذيراته: {user.warns}/{max_warns}**")
                        except Exception: pass
                        return

            if not event.text:
                await session.commit()
                return
            
            # --- حساب الرسائل والنقاط ---
            all_commands = PERCENT_COMMANDS + GAME_COMMANDS + ADMIN_COMMANDS + ["الاوامر"]
            is_command = any(event.text.lower().startswith(cmd.lower()) for cmd in all_commands)

            if not is_command:
                user.msg_count = (user.msg_count or 0) + 1
                chat.total_msgs = (chat.total_msgs or 0) + 1
                
                points_multiplier = 1
                inventory = user.inventory or {}
                multiplier_item = inventory.get("مضاعف نقاط")
                if multiplier_item and time.time() - multiplier_item.get("purchase_time", 0) < multiplier_item.get("duration_days", 0) * 86400:
                    points_multiplier = 2
                
                points_to_add = 0
                if len(event.text) >= 30: points_to_add += 3
                elif len(event.text) >= 4: points_to_add += 1
                if event.is_reply: points_to_add += 2

                if points_to_add > 0:
                    user.points = (user.points or 0) + (points_to_add * points_multiplier)
                
                # --- نظام الردود ---
                if (chat.settings or {}).get("public_replies_enabled", True):
                    all_replies = DEFAULT_REPLIES.copy()
                    custom_replies = chat.custom_replies or {}
                    all_replies.update({k.lower(): v for k, v in custom_replies.items()})
                    
                    reply_data = all_replies.get(event.text.lower())
                    
                    if reply_data:
                        reply_template = None
                        if isinstance(reply_data, dict):
                            current_rank = await get_user_rank(event.sender_id, event.chat_id)
                            
                            if current_rank >= Ranks.MAIN_DEV and "developer" in reply_data:
                                reply_list = reply_data["developer"]
                            elif current_rank >= Ranks.ADMIN and "bot_admin" in reply_data:
                                reply_list = reply_data["bot_admin"]
                            elif current_rank >= Ranks.MOD and "group_admin" in reply_data:
                                reply_list = reply_data["group_admin"]
                            elif "member" in reply_data:
                                reply_list = reply_data["member"]
                            else:
                                reply_list = next((v for v in reply_data.values() if isinstance(v, list)), None)
                            
                            if reply_list:
                                reply_template = random.choice(reply_list)
                        
                        elif isinstance(reply_data, str):
                            reply_template = reply_data

                        if reply_template:
                            try:
                                sender = await event.get_sender()
                                final_reply = reply_template.format(
                                    user_mention=f"[{sender.first_name}](tg://user?id={sender.id})",
                                    user_first_name=sender.first_name
                                )
                                await event.reply(final_reply)
                            except KeyError:
                                await event.reply(reply_template)
                            except Exception as e:
                                logger.error(f"خطأ في إرسال الرد: {e}")
            
            await session.commit()
        except events.StopPropagation:
            pass # هذا استثناء طبيعي لإيقاف المعالجة، لا تقم بأي إجراء
        except Exception as e:
            logger.error(f"استثناء غير معالج في general_message_handler: {e}", exc_info=True)
            await session.rollback()

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
                    
                    formatted_message = welcome_message.format(
                        user=f"[{user_entity.first_name}](tg://user?id={user_entity.id})",
                        group=chat_entity.title
                    )
                    await client.send_message(event.chat_id, formatted_message)

                await session.commit()
            except Exception as e:
                logger.error(f"خطأ في معالج انضمام الأعضاء: {e}", exc_info=True)
                await session.rollback()
