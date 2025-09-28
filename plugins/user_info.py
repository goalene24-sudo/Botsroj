import random
import re
from telethon import events

# استيرادات محلية
from bot import client

# --- دالة موحدة لتحديد المستخدم المستهدف ---
async def get_target_user(event):
    """
    تحدد المستخدم المستهدف بناءً على ما إذا كانت الرسالة ردًا أم لا.
    """
    if event.reply_to_msg_id:
        reply_message = await event.get_reply_message()
        if reply_message and reply_message.from_id:
            target_user = await client.get_entity(reply_message.from_id.user_id)
            # التأكد من أننا لا نستهدف بوت آخر
            if target_user and not target_user.bot:
                return target_user
    # إذا لم يكن هناك رد، أو فشل في الحصول على المستخدم، استهدف المرسل نفسه
    return await event.get_sender()

# --- معالج أوامر الصور ---
@client.on(events.NewMessage(pattern=r"^(صورتي|صورته)$", func=lambda e: e.is_group))
async def photo_handler(event):
    target_user = await get_target_user(event)
    if not target_user:
        return await event.reply("لا يمكنني العثور على هذا المستخدم.")

    photos = await client.get_profile_photos(target_user.id, limit=1)

    if photos:
        beauty_percentage = random.randint(70, 100)
        caption = f"**🖼️ | صورة [{target_user.first_name}](tg://user?id={target_user.id})**\n**✨ | نسبة جماله/ها: {beauty_percentage}%**"
        await event.reply(caption, file=photos[0])
    else:
        await event.reply(f"**عذرًا، لم أجد أي صور شخصية لـ [{target_user.first_name}](tg://user?id={target_user.id}).**")

# --- معالج الأوامر النصية (اسمي، معرفي، رابطي...) ---
@client.on(events.NewMessage(pattern=r"^(اسمي|اسمه|معرفي|معرفه|رابطي|رابطه)$", func=lambda e: e.is_group))
async def info_handler(event):
    command = event.text.strip()
    target_user = await get_target_user(event)
    
    if not target_user:
        return await event.reply("لا يمكنني العثور على هذا المستخدم.")

    response_text = ""
    
    if command in ["اسمي", "اسمه"]:
        response_text = f"**🏷️ | اسمك:** `{target_user.first_name}`" if event.sender == target_user else f"**🏷️ | اسمه:** `{target_user.first_name}`"
    
    elif command in ["معرفي", "معرفه"]:
        username = f"@{target_user.username}" if target_user.username else "**لا يوجد معرف**"
        response_text = f"**🆔 | معرفك:** {username}" if event.sender == target_user else f"**🆔 | معرفه:** {username}"

    elif command in ["رابطي", "رابطه"]:
        link = f"https://t.me/{target_user.username}" if target_user.username else f"**[اضغط هنا](tg://user?id={target_user.id})**"
        response_text = f"**🔗 | رابط حسابك:** {link}" if event.sender == target_user else f"**🔗 | رابط حسابه:** {link}"

    await event.reply(response_text)