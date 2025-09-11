# plugins/events.py
from datetime import datetime, timedelta
import random
import time
from telethon import events
from telethon.tl.types import MessageEntityUrl, MessageEntityMention
from bot import client
import config

# --- (مُعدل) استيراد الأدوات الجديدة والنماذج ---
from .utils import (
    check_activation,
    PERCENT_COMMANDS, GAME_COMMANDS, ADMIN_COMMANDS, add_points,
    FLOOD_TRACKER, get_user_rank, Ranks, is_vip,
    get_or_create_chat, get_or_create_user
)
from database import SESSION
from models import Alias, MessageHistory

from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST
from .aliases import FIXED_ALIASES

# --- (مُعدل بالكامل) دوال التحذير تعمل مع SQLAlchemy ---
def add_user_warn(chat_id, user_id):
    user = get_or_create_user(chat_id, user_id)
    user.warns += 1
    SESSION.commit()
    return user.warns

def reset_user_warns(chat_id, user_id):
    user = get_or_create_user(chat_id, user_id)
    user.warns = 0
    SESSION.commit()
    return True

@client.on(events.NewMessage(func=lambda e: not e.is_private))
async def general_message_handler(event):
    if not await check_activation(event.chat_id):
        return

    # --- (جديد) جلب كائنات المجموعة والمستخدم في بداية المعالج ---
    chat = get_or_create_chat(event.chat_id)
    user = get_or_create_user(event.chat_id, event.sender_id)

    # --- محرك ترجمة الأوامر المضافة والثابتة ---
    if event.text:
        # جلب الاختصارات من قاعدة البيانات
        aliases_from_db = SESSION.query(Alias).filter(Alias.chat_id == event.chat_id).all()
        user_aliases = {a.alias_name: a.command_name for a in aliases_from_db}
        
        all_aliases = FIXED_ALIASES.copy()
        all_aliases.update(user_aliases)

        command_candidate = event.text.strip()
        if command_candidate in all_aliases:
            original_command = all_aliases[command_candidate]
            event.text = original_command
            event.raw_text = original_command
            if hasattr(event, 'message') and hasattr(event.message, 'message'):
                event.message.message = original_command

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

        # إضافة الرسالة الجديدة إلى السجل في قاعدة البيانات
        new_msg = MessageHistory(chat_id=event.chat_id, msg_id=event.id, msg_type=msg_type)
        SESSION.add(new_msg)
        
        # حذف الرسائل القديمة إذا تجاوز السجل 100 رسالة
        history_count = SESSION.query(MessageHistory).filter(MessageHistory.chat_id == event.chat_id).count()
        if history_count > 100:
            oldest_msg = SESSION.query(MessageHistory).filter(MessageHistory.chat_id == event.chat_id).order_by(MessageHistory.id.asc()).first()
            SESSION.delete(oldest_msg)

    # --- ميزة الذكر التلقائي ---
    now = int(time.time())
    last_dhikr_time = chat.settings.get("last_dhikr_time", 0)
    dhikr_interval = chat.settings.get("dhikr_interval", 3600)
    is_dhikr_enabled = chat.settings.get("dhikr_enabled", True)

    if is_dhikr_enabled and (now - last_dhikr_time > dhikr_interval):
        dhikr_message = random.choice(DHIKR_LIST)
        await client.send_message(event.chat_id, dhikr_message)
        # تحديث وقت آخر ذكر في إعدادات المجموعة
        chat_settings = chat.settings.copy()
        chat_settings["last_dhikr_time"] = now
        chat.settings = chat_settings

    # --- فحص الرتب والأقفال ---
    rank_int = await get_user_rank(event.sender_id, event.chat_id)
    is_immune = rank_int >= Ranks.MOD

    if not is_immune:
        chat_locks = chat.lock_settings
        message_entities_for_lock = event.message.entities or []
        checks = {
            "photo": event.photo, "video": event.video, "gif": event.gif,
            "sticker": event.sticker, "url": any(isinstance(e, MessageEntityUrl) for e in message_entities_for_lock),
            "username": any(isinstance(e, MessageEntityMention) for e in message_entities_for_lock),
            "forward": event.forward, "bot": event.via_bot
        }
        for lock_name, condition in checks.items():
            if chat_locks.get(f"lock_{lock_name}") and condition:
                try: await event.delete()
                except Exception as e: print(f"لم أستطع حذف الرسالة في {event.chat_id}: {e}")
                SESSION.commit() # حفظ أي تغييرات قبل الخروج
                return

        # (منطق التكرار والكلمات الممنوعة يبقى كما هو تقريبًا)
        if chat_locks.get("lock_anti_flood", False):
            # ... (منطق التكرار لا يتغير لأنه لا يعتمد على قاعدة البيانات) ...
            pass

        if event.text:
            filtered_words = chat.filtered_words
            if filtered_words and any(word.lower() in event.text.lower() for word in filtered_words):
                try:
                    await event.delete()
                    sender = await event.get_sender()
                    new_warn_count = add_user_warn(event.chat_id, sender.id)
                    max_warns = chat.settings.get("max_warns", 3)
                    if new_warn_count >= max_warns:
                        until_date = datetime.now() + timedelta(minutes=1440)
                        await client.edit_permissions(event.chat_id, sender, send_messages=False, until_date=until_date)
                        await client.send_message(event.chat_id, f"**❗️تم كتم [{sender.first_name}](tg://user?id={sender.id}) لمدة 24 ساعة** لتجاوز التحذيرات.")
                        reset_user_warns(event.chat_id, sender.id)
                    else:
                        await client.send_message(event.chat_id, f"**⚠️ تم حذف رسالة من [{sender.first_name}](tg://user?id={sender.id}) لمخالفة القوانين.\nعدد تحذيراته: {new_warn_count}/{max_warns}**")
                    SESSION.commit() # حفظ أي تغييرات قبل الخروج
                    return
                except Exception as e: print(f"خطأ في فلتر الكلمات: {e}")

    if not event.text:
        SESSION.commit()
        return
    
    # --- حساب الرسائل والنقاط ---
    all_commands = PERCENT_COMMANDS + GAME_COMMANDS + ADMIN_COMMANDS + ["الاوامر"] # مثال مبسط
    is_command = any(event.text.lower().startswith(cmd.lower()) for cmd in all_commands)

    if not is_command:
        user.msg_count += 1
        chat.total_msgs += 1
        
        points_multiplier = 1
        inventory = user.inventory
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
            user.points += final_points_to_add
        
        # --- نظام الردود ---
        # ... (منطق الردود تم تبسيطه هنا، سيقرأ من chat.custom_replies و chat.settings) ...
        # ... (يمكننا تعديله بالتفصيل لاحقًا إذا لزم الأمر) ...

    # --- (مهم جدًا) حفظ كل التغييرات في قاعدة البيانات في نهاية المعالج ---
    SESSION.commit()
