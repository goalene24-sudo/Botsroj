import logging
import re
from telethon import events

from bot import client
from database import AsyncDBSession
from models import User
from sqlalchemy.future import select

from .utils import check_activation, get_or_create_user

logger = logging.getLogger(__name__)

# --- دالة مساعدة لتنظيف اسم المستخدم ---
def clean_username(username: str) -> str:
    # إزالة @ والمسافات الزائدة
    cleaned = username.strip().replace("@", "")
    # التحقق من أن الاسم يحتوي فقط على أحرف وأرقام و . و _
    if re.match(r"^[a-zA-Z0-9_.]+$", cleaned):
        return cleaned
    return None


@client.on(events.NewMessage(pattern=r"^[!/]ربط_(انستا|تويتر) (.+)"))
async def link_socials_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    platform = event.pattern_match.group(1)
    username_raw = event.pattern_match.group(2)
    
    username = clean_username(username_raw)
    
    if not username:
        return await event.reply("**❌ | اسم المستخدم الذي أدخلته غير صالح.**\nيجب أن يحتوي فقط على أحرف إنجليزية، أرقام، `_` أو `.`.")

    async with AsyncDBSession() as session:
        # نحصل على المستخدم من قاعدة البيانات بناءً على المجموعة الحالية
        user = await get_or_create_user(session, event.chat_id, event.sender_id)
        
        if platform == "انستا":
            user.instagram_username = username
            platform_name = "انستغرام"
            icon = "📸"
        else: # تويتر
            user.twitter_username = username
            platform_name = "تويتر"
            icon = "🐦"
            
        await session.commit()

    await event.reply(f"**{icon} | تم ربط حسابك في {platform_name} بنجاح.**\n**اسم المستخدم:** `{username}`")