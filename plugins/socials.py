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


@client.on(events.NewMessage(pattern=r"^ربط_(انستا|تويتر) (.+)"))
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

# =========================================================
# | START OF NEW CODE | بداية الكود الجديد لأمر الحذف      |
# =========================================================
@client.on(events.NewMessage(pattern=r"^حذف_حساب (انستا|تويتر)$"))
async def unlink_socials_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    platform = event.pattern_match.group(1)

    async with AsyncDBSession() as session:
        user_result = await session.execute(
            select(User).where(User.chat_id == event.chat_id, User.user_id == event.sender_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            # هذا الشرط احتياطي، لأن المستخدم يتم إنشاؤه تلقائياً
            return await event.reply("**حدث خطأ، لم يتم العثور على ملفك الشخصي.**")

        if platform == "انستا":
            if not user.instagram_username:
                return await event.reply("**⚠️ | لم تقم بربط حساب انستغرام أصلاً.**")
            user.instagram_username = None
            platform_name = "انستغرام"
            icon = "📸"
        else: # تويتر
            if not user.twitter_username:
                return await event.reply("**⚠️ | لم تقم بربط حساب تويتر أصلاً.**")
            user.twitter_username = None
            platform_name = "تويتر"
            icon = "🐦"
            
        await session.commit()

    await event.reply(f"**🗑️ | تم حذف ربط حسابك في {platform_name} بنجاح.**")
# =========================================================
# | END OF NEW CODE | نهاية الكود الجديد                   |
# =========================================================
