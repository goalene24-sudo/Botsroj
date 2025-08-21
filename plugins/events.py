# plugins/events.py
from datetime import datetime, timedelta
import random
import time
from telethon import events
from telethon.tl.types import MessageEntityUrl, MessageEntityMention
from bot import client
import config
from .utils import (
    db, save_db, is_admin, check_activation,
    PERCENT_COMMANDS, GAME_COMMANDS, ADMIN_COMMANDS, add_points,
    FLOOD_TRACKER, get_user_rank
)
from .default_replies import DEFAULT_REPLIES
from .dhikr_data import DHIKR_LIST

def add_user_warn(chat_id, user_id):
    chat_id_str, user_id_str = str(chat_id), str(user_id)
    if "warns" not in db.get(chat_id_str, {}): db[chat_id_str]["warns"] = {}
    new_warns = db[chat_id_str]["warns"].get(user_id_str, 0) + 1
    db[chat_id_str]["warns"][user_id_str] = new_warns
    save_db(db)
    return new_warns

def reset_user_warns(chat_id, user_id):
    chat_id_str, user_id_str = str(chat_id), str(user_id)
    if "warns" in db.get(chat_id_str, {}) and user_id_str in db[chat_id_str]["warns"]:
        del db[chat_id_str]["warns"][user_id_str]
        save_db(db)
        return True
    return False

@client.on(events.NewMessage(func=lambda e: not e.is_private))
async def general_message_handler(event):
    if not await check_activation(event.chat_id): 
        return
        
    chat_id_str, user_id_str = str(event.chat_id), str(event.sender_id)

    # --- ميزة الذكر التلقائي ---
    now = int(time.time())
    last_dhikr_time = db.get(chat_id_str, {}).get("last_dhikr_time", 0)
    # 3600 ثانية = 1 ساعة
    if now - last_dhikr_time > 3600:
        dhikr_message = random.choice(DHIKR_LIST)
        await client.send_message(event.chat_id, dhikr_message)
        if chat_id_str not in db: db[chat_id_str] = {}
        db[chat_id_str]["last_dhikr_time"] = now
        save_db(db)
    # --- نهاية ميزة الذكر التلقائي ---

    if not event.text: return
    
    service_commands = ["اضف كلمة ممنوعة", "حذف كلمة ممنوعة", "الكلمات الممنوعة", "تاك للكل", "@all", "طقس", "معلومات المجموعة", "احصائيات", "ضع رد المطور", "ضع رد المناداة", "مسح رد المطور", "مسح رد المناداة", "احجي", "حظي", "فككها", "صندوق الحظ", "ضع ترحيب", "حذف الترحيب", "تثبيت", "تفعيل الصراحة هنا", "تعطيل الصراحة هنا", "ضع قناة سجل الصراحة", "سبحة", "اسماء الله الحسنى", "سيرة النبي", "ضع قوانين", "القوانين", "حذف القوانين", "نشاطك", "عمري"]
    all_commands = PERCENT_COMMANDS + GAME_COMMANDS + ADMIN_COMMANDS + ["الاوامر", "الردود", "ايدي", "id", "اضف رد", "حذف رد", "تفعيل", "ايقاف", "تحذير", "حذف التحذيرات", "اذكار الصباح", "اذكار المساء", "راتب", "ضع نبذة", "المتجر", "شراء", "طلاق", "ممتلكاتي", "نقاطي", "صديقي المفضل", "حذف صديقي المفضل", "ضع ميلادي"] + service_commands + ["حللني", "حلل", "لو خيروك", "تحدي نرد", "ميمز", "سمايلات", "سمايل"]
    is_command = any(event.text.startswith(cmd) for cmd in all_commands) or event.text.startswith("اذان")

    if is_command:
        return

    rank = await get_user_rank(event)
    is_admin_or_dev = rank in ["developer", "bot_admin", "group_admin"]

    # النظام الذكي لاحتساب النقاط
    if "users" not in db.get(chat_id_str, {}): db[chat_id_str]["users"] = {}
    if user_id_str not in db[chat_id_str]["users"]:
        join_date = datetime.now().strftime("%Y-%m-%d")
        db[chat_id_str]["users"][user_id_str] = {"msg_count": 0, "points": 0, "join_date": join_date, "sahaqat": 0}
    
    if "sahaqat" not in db[chat_id_str]["users"][user_id_str]:
        db[chat_id_str]["users"][user_id_str]["sahaqat"] = 0

    db[chat_id_str]["users"][user_id_str]["msg_count"] = db[chat_id_str]["users"][user_id_str].get("msg_count", 0) + 1
    db[chat_id_str]["total_msgs"] = db.get(chat_id_str, {}).get("total_msgs", 0) + 1
    
    points_multiplier = 1
    user_data = db[chat_id_str]["users"][user_id_str]
    inventory = user_data.get("inventory", {})
    multiplier_item = inventory.get("مضاعف نقاط")

    if multiplier_item:
        purchase_time = multiplier_item.get("purchase_time", 0)
        duration_days = multiplier_item.get("duration_days", 0)
        duration_seconds = duration_days * 24 * 60 * 60
        if time.time() - purchase_time < duration_seconds:
            points_multiplier = 2
    
    points_to_add = 0
    message_length = len(event.text)
    
    if message_length >= 30: points_to_add += 3
    elif message_length >= 4: points_to_add += 1
    
    if event.is_reply: points_to_add += 2

    final_points_to_add = points_to_add * points_multiplier
    if final_points_to_add > 0:
        add_points(event.chat_id, event.sender_id, final_points_to_add)
    
    save_db(db)
    
    if not event.is_reply:
        if event.text == "سروج":
            if rank == "developer": reply = db.get(chat_id_str, {}).get("dev_reply", "أمرني مطوري الغالي 👑")
            else: reply = db.get(chat_id_str, {}).get("call_reply", "عيوني! بس مو مثل عيون المطور 😉")
            await event.reply(f"**{reply}**")
            return

        custom_replies = db.get(chat_id_str, {}).get("custom_replies", {})
        if event.text in custom_replies:
            reply_text = custom_replies[event.text]
            if rank == "developer": final_reply = f"**لك يا مطوري 🫡:**\n**{reply_text}**"
            else: final_reply = f"**{reply_text}**"
            await event.reply(final_reply)
        elif event.text in DEFAULT_REPLIES:
            reply_options_for_trigger = DEFAULT_REPLIES[event.text]
            replies_for_rank = reply_options_for_trigger.get(rank, reply_options_for_trigger.get("member"))
            if replies_for_rank:
                chosen_reply = random.choice(replies_for_rank)
                final_reply = chosen_reply.replace("@USER", "@tit_50")
                await event.reply(f'**{final_reply}**')

    if is_admin_or_dev:
        return
    
    filtered_words = db.get(chat_id_str, {}).get("filtered_words", [])
    if filtered_words and any(word.lower() in event.text.lower() for word in filtered_words):
        try:
            await event.delete()
            sender = await event.get_sender()
            new_warn_count = add_user_warn(event.chat_id, sender.id)
            if new_warn_count >= 3:
                until_date = datetime.now() + timedelta(minutes=1440)
                await client.edit_permissions(event.chat_id, sender, send_messages=False, until_date=until_date)
                await client.send_message(event.chat_id, f"**❗️تم كتم [{sender.first_name}](tg://user?id={sender.id}) لمدة 24 ساعة** لتجاوز التحذيرات.")
                reset_user_warns(event.chat_id, sender.id)
            else:
                await client.send_message(event.chat_id, f"**⚠️ تم حذف رسالة من [{sender.first_name}](tg://user?id={sender.id}) لمخالفة القوانين.\nعدد تحذيراته: {new_warn_count}/3**")
            return
        except Exception as e: print(f"خطأ في فلتر الكلمات: {e}")

    chat_locks = db.get(chat_id_str, {})
    if chat_locks.get("anti_flood", False):
        now = datetime.now()
        if chat_id_str not in FLOOD_TRACKER: FLOOD_TRACKER[chat_id_str] = {}
        if user_id_str not in FLOOD_TRACKER[chat_id_str]: FLOOD_TRACKER[chat_id_str][user_id_str] = []
        FLOOD_TRACKER[chat_id_str][user_id_str].append(now)
        FLOOD_TRACKER[chat_id_str][user_id_str] = [t for t in FLOOD_TRACKER[chat_id_str][user_id_str] if now - t < timedelta(seconds=5)]
        if len(FLOOD_TRACKER[chat_id_str][user_id_str]) > 5:
            try:
                await client.edit_permissions(event.chat_id, event.sender_id, send_messages=False, until_date=now + timedelta(minutes=1))
                await event.reply(f"**لزكت يمعود! [{event.sender.first_name}](tg://user?id={event.sender.id}) انلصمت لدقيقة بسبب التكرار.**")
                FLOOD_TRACKER[chat_id_str][user_id_str] = []
            except Exception as e: print(f"خطأ في كتم التكرار: {e}")
            return
            
    message_entities = event.message.entities or []
    checks = {"photo": event.photo, "video": event.video, "gif": event.document and 'image/gif' in event.document.mime_type, "sticker": event.sticker, "url": any(isinstance(e, MessageEntityUrl) for e in message_entities), "username": any(isinstance(e, MessageEntityMention) for e in message_entities), "forward": event.forward, "bot": event.via_bot}
    for lock_name, condition in checks.items():
        if chat_locks.get(lock_name) and condition:
            try: await event.delete()
            except Exception as e: print(f"لم أستطع حذف الرسالة في {chat_id_str}: {e}")
            break
