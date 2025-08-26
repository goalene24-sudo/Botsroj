# plugins/id.py
import random
import time
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from bot import client
import config
from .utils import check_activation, db, is_command_enabled

RANDOM_HEADERS = [
    "شــوف الحــلو؟ 🧐", "تــعال اشــوفك 🫣", "بــاوع الجــمال 🫠",
    "تــحبني؟ 🤔", "احــبك ❤️", "هــايروحي 🥹"
]
RANDOM_TAFA3UL = [
    "سايق مخده 🛌", "ياكل تبن 🐐", "نايم بالكروب 😴", "متفاعل نار 🔥",
    "أسطورة المجموعة 👑", "مدري شيسوي 🤷‍♂️", "يخابر حبيبتة 👩‍❤️‍💋‍👨", "زعطوط الكروب 👶"
]

@client.on(events.NewMessage(pattern=r"^(ايدي|id)(?: |$)(.*)"))
async def id_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not is_command_enabled(event.chat_id, "id_enabled"):
        return await event.reply("🚫 | **عذراً، أمر الأيدي معطل في هذه المجموعة حالياً.**")
    
    target_user = None
    replied_msg = await event.get_reply_message()
    user_input = event.pattern_match.group(2)

    if replied_msg:
        target_user = await replied_msg.get_sender()
    elif user_input:
        try:
            target_user = await client.get_entity(user_input)
        except (ValueError, TypeError):
            return await event.reply("**ما لگيت هيج مستخدم.**")
    else:
        target_user = await event.get_sender()

    if not target_user:
        return await event.reply("**ما گدرت أحدد المستخدم.**")

    chat_id_str, user_id_str = str(event.chat_id), str(target_user.id)
    
    try:
        full_user = await client(GetFullUserRequest(target_user.id))
        bio = full_user.full_user.about or "ماكو بايو."
    except Exception:
        bio = "ماكو بايو."
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    msg_count = user_data.get("msg_count", 0)
    points = user_data.get("points", 0)
    sahaqat = user_data.get("sahaqat", 0)
    
    # --- التحقق من الألقاب والزخرفة ---
    inventory = user_data.get("inventory", {})
    vip_status_text = None
    custom_title = None
    decoration = ""

    # التحقق من حالة الـ VIP
    vip_item = inventory.get("لقب vip")
    if vip_item:
        purchase_time = vip_item.get("purchase_time", 0)
        duration_seconds = vip_item.get("duration_days", 0) * 86400
        if time.time() - purchase_time < duration_seconds:
            vip_status_text = "💎 | من كبار الشخصيات VIP"

    # التحقق من اللقب المخصص
    custom_title_item = inventory.get("تخصيص لقب")
    if custom_title_item:
        purchase_time = custom_title_item.get("purchase_time", 0)
        duration_seconds = custom_title_item.get("duration_days", 0) * 86400
        if time.time() - purchase_time < duration_seconds:
            custom_title = user_data.get("custom_title")
            
    # التحقق من الزخرفة
    decoration_item = inventory.get("زخرفة")
    if decoration_item:
        purchase_time = decoration_item.get("purchase_time", 0)
        duration_seconds = decoration_item.get("duration_days", 0) * 86400
        if time.time() - purchase_time < duration_seconds:
            decoration = "✨"
    # --- نهاية التحقق ---

    bot_admins = db.get(chat_id_str, {}).get("bot_admins", [])
    rank = ""
    if target_user.id in config.SUDO_USERS:
        rank = "المطور الاساسي ⚡️"
    else:
        try:
            perms = await client.get_permissions(event.chat_id, target_user.id)
            if perms.is_creator: rank = "المالك 👑"
            elif perms.is_admin: rank = "مشرف 🛡️"
            elif target_user.id in bot_admins: rank = "أدمن بالبوت ⚜️"
            else: rank = "عضو 👤"
        except:
            if target_user.id in bot_admins: rank = "أدمن بالبوت ⚜️"
            else: rank = "عضو 👤"

    header = random.choice(RANDOM_HEADERS)
    tafa3ul = random.choice(RANDOM_TAFA3UL)
    
    caption = f"**{header}**\n\n"
    
    if vip_status_text:
        caption += f"**{vip_status_text}**\n"
        
    caption += (
        f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**\n"
        f"**- ايديك:** `{target_user.id}`\n"
        f"**- معرفك:** @{target_user.username or 'لا يوجد'}\n"
        f"**- حسابك:** [{target_user.first_name}](tg://user?id={target_user.id}) {decoration}\n"
        f"**- رتبتك:** {rank}\n"
    )
    
    if custom_title:
        caption += f"**- لقبك:** {custom_title}\n"
        
    caption += (
        f"**- تفاعلك:** {tafa3ul}\n"
        f"**- رسائلك:** `{msg_count}`\n"
        f"**- سحكاتك:** `{sahaqat}`\n"
        f"**- نقاطك:** `{points}`\n"
        f"**- البايو:** {bio}\n"
        f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**"
    )
    
    pfp = await client.get_profile_photos(target_user, limit=1)
    if pfp:
        await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
    else:
        await event.reply(caption, reply_to=event.id)
