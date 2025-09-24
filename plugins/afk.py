import logging
from telethon import events
from datetime import datetime

from bot import client
# --- استيراد الدوال المساعدة ---
from .utils import check_activation, get_uptime_string

logger = logging.getLogger(__name__)

# قاموس لتخزين حالة المستخدمين غير المتواجدين
AFK_USERS = {}

# --- معالج أمر !afk ---
@client.on(events.NewMessage(pattern=r"^[!/]afk(?:$| (.+))"))
async def set_afk_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    chat_id = event.chat_id
    user_id = event.sender_id
    reason = event.pattern_match.group(1)

    if chat_id not in AFK_USERS:
        AFK_USERS[chat_id] = {}

    AFK_USERS[chat_id][user_id] = {
        "time": datetime.now(),
        "reason": reason or "بدون سبب"
    }

    await event.reply(f"**🌙 | تم ضبط حالتك إلى \"غير متواجد\".**\n**السبب:** {reason or 'لم يتم تحديد سبب.'}")


# --- معالج الرسائل للتحقق من حالة AFK ---
@client.on(events.NewMessage(func=lambda e: e.is_group and not e.is_private))
async def afk_checker_handler(event):
    if not await check_activation(event.chat_id):
        return
        
    # --- (تمت الإضافة هنا) تجاهل أمر afk نفسه ---
    if event.text and event.text.lower().startswith(("!afk", "/afk")):
        return

    chat_id = event.chat_id
    sender_id = event.sender_id

    # --- الجزء الأول: التحقق مما إذا كان المرسل نفسه غير متواجد ---
    if chat_id in AFK_USERS and sender_id in AFK_USERS[chat_id]:
        afk_info = AFK_USERS[chat_id].pop(sender_id)
        
        if not AFK_USERS[chat_id]:
            del AFK_USERS[chat_id]
            
        time_away = get_uptime_string(afk_info["time"])
        await event.reply(f"**☀️ | أهلاً بعودتك!**\nلقد كنت غير متواجد لمدة **{time_away}**.")

    # --- الجزء الثاني: التحقق مما إذا قام بمنشن لشخص غير متواجد ---
    if not event.message or not (event.is_reply or event.message.mentioned):
        return

    replied_to_user_id = None
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg:
            replied_to_user_id = reply_msg.sender_id

    mentioned_users_ids = []
    if event.message.entities:
        for entity, text in event.get_entities_text():
            # Corresponds to a plain @username mention
            if entity.type == 'mention':
                try:
                    mentioned_user = await client.get_entity(text)
                    mentioned_users_ids.append(mentioned_user.id)
                except Exception:
                    pass
            # Corresponds to a mention via a user's first name (a link)
            elif entity.type == 'mention_user':
                mentioned_users_ids.append(entity.user_id)

    target_users = list(set([replied_to_user_id] + mentioned_users_ids))

    if chat_id in AFK_USERS:
        for user_id in target_users:
            if user_id and user_id in AFK_USERS[chat_id]:
                afk_info = AFK_USERS[chat_id][user_id]
                time_away = get_uptime_string(afk_info["time"])
                
                try:
                    user_entity = await client.get_entity(user_id)
                    user_name = user_entity.first_name
                except Exception:
                    user_name = "هذا المستخدم"
                
                await event.reply(
                    f"**💤 | {user_name} غير متواجد حالياً.**\n"
                    f"**- منذ:** {time_away}\n"
                    f"**- السبب:** {afk_info['reason']}"
                )
                break
