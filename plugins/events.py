import asyncio
from datetime import datetime, timedelta
import random
import time
import re # <-- إضافة مكتبة الأنماط
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
    check_activation, get_user_rank, Ranks, 
    get_or_create_chat, get_or_create_user, FLOOD_TRACKER
)
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES
from .command_patterns import ALL_COMMAND_PATTERNS # <-- استيراد قائمة الأوامر الجديدة
import logging

# إعداد السجل
logger = logging.getLogger(__name__)

@client.on(events.NewMessage(func=lambda e: not e.is_private and e.chat and e.sender))
async def master_message_handler(event):
    if not await check_activation(event.chat_id):
        return

    # --- الخطوة 1: ترجمة الاختصارات أولاً ---
    if event.text:
        async with AsyncDBSession() as session:
            result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
            aliases_from_db = result.scalars().all()
            user_aliases = {a.alias_name: a.command_name for a in aliases_from_db}
        
        all_aliases = FIXED_ALIASES.copy()
        all_aliases.update(user_aliases)

        command_candidate = event.text.strip()
        if command_candidate in all_aliases:
            original_command = all_aliases[command_candidate]
            event.message.message = original_command
            event.raw_text = original_command

    # --- الخطوة 2: التحقق إذا كانت الرسالة أمرًا باستخدام القائمة الجديدة ---
    if event.text:
        is_command = False
        for pattern in ALL_COMMAND_PATTERNS:
            # استخدام re.match للتحقق من تطابق النمط مع بداية الرسالة
            if re.match(pattern, event.text):
                is_command = True
                break
        
        # إذا كانت الرسالة أمرًا، توقف هنا ودع المعالج المختص يكمل
        if is_command:
            return

    # --- الخطوة 3: إذا لم تكن الرسالة أمرًا، قم بتنفيذ المهام العامة ---
    async with AsyncDBSession() as session:
        try:
            chat = await get_or_create_chat(session, event.chat_id)
            user = await get_or_create_user(session, event.chat_id, event.sender_id)

            # ... (بقية منطق الأقفال، الفلترة، حساب النقاط، والردود التلقائية) ...
            # هذا الكود لن يعمل إلا على الرسائل العادية الآن
            
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
            
            if (chat.settings or {}).get("public_replies_enabled", True):
                all_replies = DEFAULT_REPLIES.copy()
                custom_replies = chat.custom_replies or {}
                all_replies.update({k.lower(): v for k, v in custom_replies.items()})
                reply_data = all_replies.get(event.text.lower())
                if reply_data:
                    reply_template = ""
                    if isinstance(reply_data, dict):
                        current_rank = await get_user_rank(event.sender_id, event.chat_id)
                        if current_rank >= Ranks.MAIN_DEV and "developer" in reply_data: reply_list = reply_data["developer"]
                        elif current_rank >= Ranks.ADMIN and "bot_admin" in reply_data: reply_list = reply_data["bot_admin"]
                        elif current_rank >= Ranks.MOD and "group_admin" in reply_data: reply_list = reply_data["group_admin"]
                        elif "member" in reply_data: reply_list = reply_data["member"]
                        else: reply_list = next((v for v in reply_data.values() if isinstance(v, list)), None)
                        if reply_list: reply_template = random.choice(reply_list)
                    elif isinstance(reply_data, str): reply_template = reply_data
                    if reply_template:
                        try:
                            sender = await event.get_sender()
                            final_reply = reply_template.format(user_mention=f"[{sender.first_name}](tg://user?id={sender.id})", user_first_name=sender.first_name)
                            await event.reply(final_reply)
                        except KeyError: await event.reply(reply_template)
                        except Exception as e: logger.error(f"خطأ في إرسال الرد: {e}")
            
            await session.commit()
        except Exception as e:
            logger.error(f"استثناء غير معالج في general_message_handler: {e}", exc_info=True)
            await session.rollback()

# --- معالج انضمام الأعضاء (يبقى كما هو) ---
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
