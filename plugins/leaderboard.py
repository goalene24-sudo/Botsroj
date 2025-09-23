import logging
from telethon import events
from sqlalchemy.future import select
from sqlalchemy import func

from bot import client
# --- استيراد مكونات قاعدة البيانات ---
from database import AsyncDBSession
from models import User

# --- استيراد الدوال المساعدة ---
from .utils import check_activation

logger = logging.getLogger(__name__)

# --- دالة لوحة الصدارة ---
async def show_leaderboard(event):
    """
    تقوم هذه الدالة بجلب أكثر 10 أعضاء تفاعلاً في المجموعة وعرضهم.
    """
    if event.is_private or not await check_activation(event.chat_id):
        return

    try:
        processing_message = await event.reply("**🏆 | جاري حساب ملوك التفاعل... لحظات.**")

        top_users_records = []
        async with AsyncDBSession() as session:
            result = await session.execute(
                select(User)
                .where(User.chat_id == event.chat_id)
                .order_by(User.msg_count.desc())
                .limit(10)
            )
            top_users_records = result.scalars().all()

        if not top_users_records:
            return await processing_message.edit("**🤔 | لا توجد بيانات تفاعل كافية لعرض القائمة بعد.**")

        leaderboard_text = "**🏆 | ملوك التفاعل في المجموعة:**\n\n"
        
        rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        for i, user_record in enumerate(top_users_records, 1):
            
            # =========================================================
            # | START OF MODIFIED CODE | بداية الكود المعدل            |
            # =========================================================
            try:
                user_entity = await client.get_entity(user_record.user_id)
                # بناء "منشن" قابل للضغط باستخدام اسم المستخدم والـ ID
                user_display_name = f"[{user_entity.first_name}](tg://user?id={user_record.user_id})"
            except Exception:
                # في حال لم يتم العثور على المستخدم، نعرض نصاً عادياً
                user_display_name = "عضو غادر"
            # =========================================================
            # | END OF MODIFIED CODE | نهاية الكود المعدل              |
            # =========================================================

            lrm = "\u200e"
            emoji = rank_emojis.get(i, "")
            
            leaderboard_text += f"{lrm}**{i}.** {user_display_name}{lrm} ~ (`{user_record.msg_count}` رسالة){f' {emoji}' if emoji else ''}\n"

        await processing_message.edit(leaderboard_text)

    except Exception as e:
        logger.error(f"Error in show_leaderboard: {e}", exc_info=True)
        await event.reply("**حدث خطأ أثناء جلب قائمة المتفاعلين.**")
