# plugins/id.py
import random
import time
from telethon import events
from bot import client
import config
from .utils import check_activation, db, get_user_rank, Ranks, is_command_enabled
# (تمت الإضافة) استدعاء قاموس الأوسمة
from .achievements import ACHIEVEMENTS

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
    
    # --- جلب كل بيانات المستخدم ---
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    msg_count = user_data.get("msg_count", 0)
    points = user_data.get("points", 0)
    sahaqat = user_data.get("sahaqat", 0)
    # (تم الإصلاح) جلب النبذة من قاعدة بيانات البوت
    custom_bio = user_data.get("bio", "لم يتم تعيين نبذة بعد.")
    
    # --- جلب الرتبة بالطريقة الموحدة ---
    rank_int = await get_user_rank(target_user.id, event)
    rank_map = {
        Ranks.DEVELOPER: "المطور 👨‍💻",
        Ranks.OWNER: "مالك المجموعة 👑",
        Ranks.CREATOR: "منشئ في البوت ⚜️",
        Ranks.BOT_ADMIN: "ادمن في البوت 🤖",
        Ranks.GROUP_ADMIN: "مشرف في المجموعة 🛡️",
        Ranks.MEMBER: "عضو 👤"
    }
    rank = rank_map.get(rank_int, "عضو 👤")
    
    # --- (جديد) جلب الأوسمة ---
    user_achievements_keys = user_data.get("achievements", [])
    badges_str = ""
    if user_achievements_keys:
        for ach_key in user_achievements_keys:
            if ach_key in ACHIEVEMENTS:
                badges_str += ACHIEVEMENTS[ach_key]["icon"]
    
    # --- التحقق من الألقاب والزخرفة ---
    inventory = user_data.get("inventory", {})
    custom_title = None
    decoration = ""

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
    
    header = random.choice(RANDOM_HEADERS)
    tafa3ul = random.choice(RANDOM_TAFA3UL)
    
    caption = f"**{header}**\n\n"
    
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
        f"**- نبذتك:** {custom_bio}\n" # (تم الإصلاح)
        f"**- تفاعلك:** {tafa3ul}\n"
        f"**- رسائلك:** `{msg_count}`\n"
        f"**- سحكاتك:** `{sahaqat}`\n"
        f"**- نقاطك:** `{points}`\n"
    )
    
    if badges_str:
        caption += f"**- أوسمتك:** {badges_str}\n" # (جديد)
    
    caption += f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**"
    
    pfp = await client.get_profile_photos(target_user, limit=1)
    if pfp:
        await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
    else:
        await event.reply(caption, reply_to=event.id)
