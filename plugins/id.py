# plugins/id.py

import random
import time
from telethon import events
from bot import client

# --- (مُعدل) استيراد الأدوات الجديدة من utils ---
from .utils import (
    check_activation,
    get_or_create_user,
    get_user_rank,
    Ranks,
    is_command_enabled,
)
from .achievements import ACHIEVEMENTS
from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantCreator

# --- (لا تغيير هنا) ---
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
    
    # --- (مُعدل) سيتم تحديث هذه الدالة لاحقًا لتقرأ من قاعدة البيانات ---
    # if not is_command_enabled(event.chat_id, "id_enabled"):
    #     return await event.reply("🚫 | **عذراً، أمر الأيدي معطل في هذه المجموعة حالياً.**")
    
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

    # --- (التحويل الكامل إلى SQLAlchemy) ---
    # خطوة واحدة لجلب أو إنشاء المستخدم من قاعدة البيانات الجديدة
    user_obj = get_or_create_user(event.chat_id, target_user.id)
    
    # جلب كل بيانات المستخدم مباشرة من الكائن (Object)
    msg_count = user_obj.msg_count
    points = user_obj.points
    sahaqat = user_obj.sahaqat
    custom_bio = user_obj.bio
    
    # جلب الرتبة (الدالة get_user_rank تم تعديلها في utils)
    rank_int = await get_user_rank(target_user.id, event.chat_id)
    rank_map = {
        Ranks.MAIN_DEV: "المطور الرئيسي 👨‍💻",
        Ranks.SECONDARY_DEV: "مطور ثانوي 🛠️",
        Ranks.OWNER: "مالك المجموعة 👑",
        Ranks.CREATOR: "المنشئ ⚜️",
        Ranks.ADMIN: "ادمن في البوت 🤖",
        Ranks.MOD: "مشرف في المجموعة 🛡️",
        Ranks.VIP: "عضو مميز ✨",
        Ranks.MEMBER: "عضو 👤"
    }
    rank = rank_map.get(rank_int, "عضو 👤")
    
    # جلب الأوسمة
    user_achievements_keys = user_obj.achievements
    badges_str = ""
    if user_achievements_keys:
        for ach_key in user_achievements_keys:
            if ach_key in ACHIEVEMENTS:
                badges_str += ACHIEVEMENTS[ach_key]["icon"]
    
    # التحقق من الألقاب والزخرفة من المخزون
    inventory = user_obj.inventory
    vip_status_text = None
    custom_title = None
    decoration = ""
    
    vip_item = inventory.get("لقب vip")
    if vip_item and time.time() - vip_item.get("purchase_time", 0) < vip_item.get("duration_days", 0) * 86400:
        vip_status_text = "💎 | من كبار الشخصيات VIP"

    custom_title_item = inventory.get("تخصيص لقب")
    if custom_title_item and time.time() - custom_title_item.get("purchase_time", 0) < custom_title_item.get("duration_days", 0) * 86400:
        custom_title = user_obj.custom_title
            
    decoration_item = inventory.get("زخرفة")
    if decoration_item and time.time() - decoration_item.get("purchase_time", 0) < decoration_item.get("duration_days", 0) * 86400:
        decoration = "✨"
    
    header = random.choice(RANDOM_HEADERS)
    tafa3ul = random.choice(RANDOM_TAFA3UL)
    
    # بناء الرسالة النهائية (لا تغيير في المنطق هنا)
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
        f"**- نبذتك:** {custom_bio}\n"
        f"**- تفاعلك:** {tafa3ul}\n"
        f"**- رسائلك:** `{msg_count}`\n"
        f"**- سحكاتك:** `{sahaqat}`\n"
        f"**- نقاطك:** `{points}`\n"
    )
    if badges_str:
        caption += f"**- أوسمتك:** {badges_str}\n"
    
    caption += f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**"
    
    # --- (منطق إرسال الصورة لم يتغير) ---
    pfp = await client.get_profile_photos(target_user, limit=1)
    if pfp:
        await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
    else:
        await event.reply(caption, reply_to=event.id)

# --- (مُعدل) تحديث أمر كشف ---
@client.on(events.NewMessage(pattern="^كشف$"))
async def kashf_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    replied_msg = await event.get_reply_message()
    if not replied_msg:
        return await event.reply("**⚠️ | يجب استخدام هذا الأمر بالرد على رسالة شخص.**")
        
    target_user = await replied_msg.get_sender()
    
    # جلب البيانات من قاعدة البيانات الجديدة
    user_obj = get_or_create_user(event.chat_id, target_user.id)
    rank_str = (await get_user_rank(target_user.id, event.chat_id))
    
    kashf_text = (
        f"**◇ : ايديه :** `{user_obj.user_id}`\n"
        f"**◇ : معرفه :** @{target_user.username or 'لا يوجد'}\n"
        f"**◇ : حسابه :** [{target_user.first_name}](tg://user?id={user_obj.user_id})\n"
        f"**◇ : رتبته :** {rank_str}\n"
        f"**◇ : رسائله :** `{user_obj.msg_count}`\n"
        f"**◇ : سحكاته :** `{user_obj.sahaqat}`\n"
        f"**◇ : تفاعله :** {random.choice(RANDOM_TAFA3UL)}\n"
        f"**◇ : انضمامه :** `{user_obj.join_date}`"
    )
    
    await event.reply(kashf_text)

# --- (لا تغيير هنا) أمر المالك لا يستخدم قاعدة البيانات ---
@client.on(events.NewMessage(pattern="^المالك$"))
async def owner_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    owner = None
    try:
        async for user in client.iter_participants(event.chat_id, filter=ChannelParticipantsAdmins):
            if isinstance(user.participant, ChannelParticipantCreator):
                owner = user
                break
    except Exception as e:
        return await event.reply(f"**حدث خطأ أثناء البحث عن المالك:**\n`{e}`")

    if owner:
        caption = (
            f"**👑 | مالك المجموعة هو:**\n\n"
            f"**- الاسم:** [{owner.first_name}](tg://user?id={owner.id})\n"
            f"**- الايدي:** `{owner.id}`"
        )
        
        pfp = await client.get_profile_photos(owner, limit=1)
        if pfp:
            await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
        else:
            await event.reply(caption, reply_to=event.id)
    else:
        await event.reply("**لا يمكنني تحديد مالك هذه المجموعة. قد تكون الصلاحيات محدودة.**")
