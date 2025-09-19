import random
import time
from telethon import events
from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantCreator

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import (
    check_activation,
    get_user_rank,
    Ranks,
    is_command_enabled,
)
# (ملاحظة: get_or_create_user موجودة في utils، لذا تم تبسيط الاستيراد)
from .utils import get_or_create_user
from .achievements import ACHIEVEMENTS

@client.on(events.NewMessage(pattern="^كشف$"))
async def kashf_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    replied_msg = await event.get_reply_message()
    if not replied_msg:
        return await event.reply("**⚠️ | يجب استخدام هذا الأمر بالرد على رسالة شخص.**")
        
    target_user = await replied_msg.get_sender()
    
    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, target_user.id)
    
    # --- تم التعديل هنا: إضافة event.client ---
    rank_int = await get_user_rank(event.client, target_user.id, event.chat_id)
    
    from .utils import get_rank_name
    rank_str = get_rank_name(rank_int)
    
    RANDOM_TAFA3UL_local = [
        "سايق مخده 🛌", "ياكل تبن 🐐", "نايم بالكروب 😴", "متفاعل نار 🔥",
        "أسطورة المجموعة 👑", "مدري شيسوي 🤷‍♂️", "يخابر حبيبتة 👩‍❤️‍💋‍👨", "زعطوط الكروب 👶"
    ]
    
    kashf_text = (
        f"**◇ : ايديه :** `{user_obj.user_id}`\n"
        f"**◇ : معرفه :** @{target_user.username or 'لا يوجد'}\n"
        f"**◇ : حسابه :** [{target_user.first_name}](tg://user?id={user_obj.user_id})\n"
        f"**◇ : رتبته :** {rank_str}\n"
        f"**◇ : رسائله :** `{user_obj.msg_count or 0}`\n"
        f"**◇ : سحكاته :** `{user_obj.sahaqat or 0}`\n"
        f"**◇ : تفاعله :** {random.choice(RANDOM_TAFA3UL_local)}\n"
        f"**◇ : انضمامه :** `{user_obj.join_date or 'غير مسجل'}`"
    )
    
    await event.reply(kashf_text)

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
