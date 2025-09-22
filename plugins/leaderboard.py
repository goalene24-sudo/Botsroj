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
        
        # قائمة الرموز التعبيرية للمراكز الأولى
        rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        for i, user_record in enumerate(top_users_records, 1):
            rank = rank_emojis.get(i, f"**{i}-**")
            
            try:
                # جلب اسم المستخدم من تيليجرام
                user_entity = await client.get_entity(user_record.user_id)
                user_name = user_entity.first_name
            except Exception:
                # في حال لم يتم العثور على المستخدم (غادر أو حذف حسابه)
                user_name = "عضو غادر"

            leaderboard_text += f"{rank} {user_name} ~ (`{user_record.msg_count}` رسالة)\n"

        await processing_message.edit(leaderboard_text)

    except Exception as e:
        logger.error(f"Error in show_leaderboard: {e}", exc_info=True)
        await event.reply("**حدث خطأ أثناء جلب قائمة المتفاعلين.**")