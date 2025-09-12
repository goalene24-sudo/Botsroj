import asyncio
from datetime import datetime, timedelta
import random
import time
from telethon import events
from telethon.tl.types import MessageEntityUrl, MessageEntityMention
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession  # تم التعديل هنا
from models import Alias, MessageHistory, User

# --- استيراد الأدوات المحدثة ---
from .utils import (
    check_activation, PERCENT_COMMANDS, GAME_COMMANDS, ADMIN_COMMANDS,
    FLOOD_TRACKER, get_user_rank, Ranks
)
from .admin import get_or_create_chat, get_or_create_user
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES
import logging

# إعداد السجل
logger = logging.getLogger(__name__)

@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat))
async def general_message_handler(event):
    if not await check_activation(event.chat_id):
        return

    async with AsyncDBSession() as session:  # تم التعديل هنا
        try:
            # --- جلب كائنات المجموعة والمستخدم في بداية المعالج ---
            chat = await get_or_create_chat(session, event.chat_id)
            if not chat:
                logger.error(f"فشل في جلب أو إنشاء كائن الدردشة لـ {event.chat_id}")
                return
            user = await get_or_create_user(session, event.chat_id, event.sender_id)
            if not user:
                logger.error(f"فشل في جلب أو إنشاء كائن المستخدم لـ {event.sender_id} في {event.chat_id}")
                return

            # --- محرك ترجمة الأوامر المضافة والثابتة ---
            if event.text:
                result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
                aliases_from_db = result.scalars().all()
                user_aliases = {a.alias_name: a.command_name for a in aliases_from_db}
                
                all_aliases = FIXED_ALIASES.copy()
                all_aliases.update(user_aliases)

                command_candidate = event.text.strip()
                if command_candidate in all_aliases:
                    original_command = all_aliases[command_candidate]
                    # تعديل نص الرسالة ليتم معالجتها كأمر أصلي
                    try:
                        event.message.message = original_command
                        event.raw_text = original_command
                    except Exception as e:
                        logger.error(f"فشل في تعديل نص الرسالة: {e}", exc_info=True)

            # --- نظام تخزين الرسائل مع الأنواع ---
            if event.id:
                long_text_size = chat.settings.get("long_text_size", 200)
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
            last_dhikr_time = chat.settings.get("last_dhikr_time", 0)
            dhikr_interval = chat.settings.get("dhikr_interval", 3600)
            is_dhikr_enabled = chat.settings.get("dhikr_enabled", True)

            if is_dhikr_enabled and (now - last_dhikr_time > dhikr_interval):
                dhikr_message = random.choice(DHIKR_LIST)
                await client.send_message(event.chat_id, dhikr_message)
                chat.settings["last_dhikr_time"] = now
                flag_modified(chat, "settings")  # إعلام SQLAlchemy بحدوث تغيير في حقل JSON

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
                            logger.info(f"تم حذف الرسالة {event.id} بسبب قفل {lock_name}")
                        except Exception as e:
                            logger.error(f"لم أستطع حذف الرسالة في {event.chat_id}: {e}", exc_info=True)
                        return  # الخروج من المعالج بعد حذف الرسالة

                # --- نظام التكرار ---
                if chat_locks.get("anti_flood", False):
                    user_id = event.sender_id
                    chat_id = event.chat_id
                    now = time.time()
                    
                    if chat_id not in FLOOD_TRACKER:
                        FLOOD_TRACKER[chat_id] = {}
                    if user_id not in FLOOD_TRACKER[chat_id]:
                        FLOOD_TRACKER[chat_id][user_id] = []
                    
                    FLOOD_TRACKER[chat_id][user_id].append(now)
                    
                    FLOOD_TRACKER[chat_id][user_id] = FLOOD_TRACKER[chat_id][user_id][-5:]
                    
                    if len(FLOOD_TRACKER[chat_id][user_id]) == 5 and (now - FLOOD_TRACKER[chat_id][user_id][0] < 3):
                        try:
                            until_date = datetime.now() + timedelta(minutes=5)
                            await client.edit_permissions(chat_id, user_id, send_messages=False, until_date=until_date)
                            await event.reply(f"**تم كتم [{event.sender.first_name}](tg://user?id={user_id}) لمدة 5 دقائق بسبب التكرار.**")
                            FLOOD_TRACKER[chat_id][user_id] = []
                            logger.info(f"تم كتم المستخدم {user_id} بسبب التكرار")
                        except Exception as e:
                            logger.error(f"خطأ في التحكم بالتكرار: {e}", exc_info=True)
                        return

                # --- نظام الكلمات الممنوعة ---
                if event.text:
                    filtered_words = chat.filtered_words or []
                    if filtered_words and any(word.lower() in event.text.lower() for word in filtered_words):
                        try:
                            await event.delete()
                            sender = await event.get_sender()
                            
                            user.warns = user.warns + 1 if hasattr(user, 'warns') else 1
                            
                            max_warns = chat.settings.get("max_warns", 3)
                            if user.warns >= max_warns:
                                until_date = datetime.now() + timedelta(days=1)
                                await client.edit_permissions(event.chat_id, sender.id, send_messages=False, until_date=until_date)
                                await client.send_message(event.chat_id, f"**❗️تم كتم [{sender.first_name}](tg://user?id={sender.id}) لمدة 24 ساعة** لتجاوز التحذيرات.")
                                user.warns = 0
                            else:
                                await client.send_message(event.chat_id, f"**⚠️ تم حذف رسالة من [{sender.first_name}](tg://user?id={sender.id}) لمخالفة القوانين.\nعدد تحذيراته: {user.warns}/{max_warns}**")
                            logger.info(f"تم حذف رسالة بسبب كلمة محظورة للمستخدم {sender.id}")
                        except Exception as e: 
                            logger.error(f"خطأ في فلتر الكلمات: {e}", exc_info=True)
                        return

            if not event.text:
                await session.commit()
                return
            
            # --- حساب الرسائل والنقاط ---
            all_commands = PERCENT_COMMANDS + GAME_COMMANDS + ADMIN_COMMANDS + ["الاوامر"]
            is_command = any(event.text.lower().startswith(cmd.lower()) for cmd in all_commands)

            if not is_command:
                user.msg_count = user.msg_count + 1 if hasattr(user, 'msg_count') else 1
                chat.total_msgs = chat.total_msgs + 1 if hasattr(chat, 'total_msgs') else 1
                
                points_multiplier = 1
                inventory = user.inventory or {}
                multiplier_item = inventory.get("مضاعف نقاط")
                if multiplier_item and time.time() - multiplier_item.get("purchase_time", 0) < multiplier_item.get("duration_days", 0) * 86400:
                    points_multiplier = 2
                
                points_to_add = 0
                message_length = len(event.text)
                if message_length >= 30: points_to_add += 3
                elif message_length >= 4: points_to_add += 1
                if event.is_reply: points_to_add += 2

                final_points_to_add = points_to_add * points_multiplier
                if final_points_to_add > 0:
                    user.points = user.points + final_points_to_add if hasattr(user, 'points') else final_points_to_add
                
                # --- نظام الردود ---
                if chat.settings.get("public_replies_enabled", True):
                    for key, value in DEFAULT_REPLIES.items():
                        if key == event.text.lower():
                            await event.reply(value)
                            break
                
                custom_replies = chat.custom_replies or {}
                for key, value in custom_replies.items():
                    if key == event.text.lower():
                        await event.reply(value)
                        break
        
            await session.commit()
        except Exception as e:
            logger.error(f"استثناء غير معالج في general_message_handler: {e}", exc_info=True)
            await session.rollback()  # إلغاء التغييرات في حالة الخطأ
