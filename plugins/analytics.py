import logging
from telethon import events
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import Counter

from bot import client
# --- استيراد مكونات قاعدة البيانات ---
from database import AsyncDBSession
from models import User, MessageHistory 

# --- استيراد الدوال المساعدة ---
from .utils import check_activation, is_admin

logger = logging.getLogger(__name__)

# قائمة بسيطة بالكلمات الشائعة لتجاهلها في التحليل
ARABIC_STOP_WORDS = {
    'في', 'من', 'على', 'الى', 'عن', 'هو', 'هي', 'هم', 'هن', 'هذا', 'هذه', 'ذلك', 
    'تلك', 'كان', 'يكون', 'سيكون', 'أن', 'أو', 'و', 'ثم', 'حتى', 'لكن', 'انا',
    'مع', 'ب', 'ل', 'ك', 'يا', 'ما', 'لا', 'هل', 'إذا', 'إن', 'الذي', 'التي', 'كل', 'بعض'
}

async def generate_analytics_report(event):
    """
    يقوم بإنشاء تقرير تحليلي لنشاط المجموعة في آخر 7 أيام.
    """
    if event.is_private or not await check_activation(event.chat_id):
        return

    # التأكد من أن المستخدم هو مشرف في المجموعة
    if not await is_admin(client, event.chat_id, event.sender_id):
        return await event.reply("**📊 | هذا الأمر مخصص للمشرفين فقط.**")

    try:
        processing_message = await event.reply("📊 | **جاري تحليل بيانات المجموعة... قد يستغرق هذا بعض الوقت.**")
        
        chat_id = event.chat_id
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        async with AsyncDBSession() as session:
            # 1. حساب الرسائل اليومية
            daily_messages_result = await session.execute(
                select(func.date(MessageHistory.timestamp, '+3 hours'), func.count(MessageHistory.id))
                .where(MessageHistory.chat_id == chat_id, MessageHistory.timestamp >= start_date)
                .group_by(func.date(MessageHistory.timestamp, '+3 hours'))
                .order_by(func.date(MessageHistory.timestamp, '+3 hours'))
            )
            daily_messages = {datetime.strptime(date, '%Y-%m-%d').strftime('%A'): count for date, count in daily_messages_result.all()}

            # 2. حساب الساعات الأكثر نشاطاً
            hourly_activity_result = await session.execute(
                # --- (تم التعديل هنا) إضافة 3 ساعات لتعديل التوقيت إلى UTC+3 ---
                select(func.strftime('%H', MessageHistory.timestamp, '+3 hours'), func.count(MessageHistory.id))
                .where(MessageHistory.chat_id == chat_id, MessageHistory.timestamp >= start_date)
                .group_by(func.strftime('%H', MessageHistory.timestamp, '+3 hours'))
                .order_by(func.count(MessageHistory.id).desc())
                .limit(3)
            )
            top_hours = hourly_activity_result.all()

            # 3. حساب الكلمات الأكثر استخداماً
            all_messages_text_result = await session.execute(
                select(MessageHistory.message_text)
                .where(MessageHistory.chat_id == chat_id, MessageHistory.timestamp >= start_date)
            )
            all_words = []
            for (text,) in all_messages_text_result.all():
                if text:
                    words = text.replace('.', '').replace(',', '').replace('?', '').replace('!', '').split()
                    all_words.extend([word for word in words if word.lower() not in ARABIC_STOP_WORDS and len(word) > 2])
            
            most_common_words = Counter(all_words).most_common(5)

            # 4. حساب الأعضاء الجدد
            new_members_count_result = await session.execute(
                select(func.count(User.id))
                .where(User.chat_id == chat_id, User.join_date >= start_date.strftime('%Y-%m-%d'))
            )
            new_members_count = new_members_count_result.scalar_one()

        # --- بناء التقرير النهائي ---
        report = f"**📊 | تقرير أداء المجموعة لآخر 7 أيام**\n\n"
        report += "**🗓️ | الرسائل اليومية:**\n"
        if daily_messages:
            max_msgs = max(daily_messages.values()) if daily_messages else 1
            for day, count in daily_messages.items():
                bar = '█' * int((count / max_msgs) * 15)
                report += f"`{day.ljust(9)}:` {bar} ({count})\n"
        else:
            report += "لا توجد رسائل مسجلة.\n"
        
        report += "\n**⏰ | الساعات الذهبية (الأكثر نشاطاً):**\n"
        if top_hours:
            for i, (hour, count) in enumerate(top_hours, 1):
                hour_int = int(hour)
                period = "صباحاً" if hour_int < 12 else "مساءً"
                display_hour = hour_int if hour_int < 13 else hour_int - 12
                display_hour = 12 if hour_int == 12 else (12 if hour_int == 0 else display_hour)
                report += f"**{i}-** الساعة {display_hour} {period} ({count} رسالة)\n"
        else:
            report += "لا توجد بيانات كافية.\n"

        report += "\n**🗣️ | الكلمات الأكثر تداولاً:**\n"
        if most_common_words:
            for i, (word, count) in enumerate(most_common_words, 1):
                report += f"**{i}-** `{word}` (تكررت {count} مرة)\n"
        else:
            report += "لا توجد كلمات مسجلة.\n"
            
        report += f"\n**👋 | الأعضاء الجدد:** انضم **{new_members_count}** عضو جديد هذا الأسبوع."
        
        await processing_message.edit(report)

    except Exception as e:
        logger.error(f"Error in generate_analytics_report: {e}", exc_info=True)
        await event.reply("**حدث خطأ أثناء إنشاء التقرير. قد لا تكون بيانات الرسائل مسجلة بعد.**")
