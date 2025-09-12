# plugins/achievements.py

from datetime import datetime
from telethon import events
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- (تم التعديل) استيراد المكونات الجديدة لقاعدة البيانات ---
from .utils import check_activation, get_or_create_user
from database import AsyncDBSession

# --- تعريف الأوسمة وشروطها ---
# يمكننا إضافة المزيد من الأوسمة هنا بسهولة في المستقبل
ACHIEVEMENTS = {
    # --- أوسمة تعتمد على عدد الرسائل ---
    "chatterbox_1": {"name": "المتحدث", "icon": "💬", "type": "messages", "value": 1000, "desc": "للوصول إلى 1,000 رسالة"},
    "chatterbox_2": {"name": "الثرثار", "icon": "🗣️", "type": "messages", "value": 5000, "desc": "للوصول إلى 5,000 رسالة"},
    "chatterbox_3": {"name": "ملك السوالف", "icon": "👑", "type": "messages", "value": 10000, "desc": "للوصول إلى 10,000 رسالة"},
    
    # --- أوسمة تعتمد على عدد النقاط ---
    "rich_1": {"name": "الغني", "icon": "💰", "type": "points", "value": 50000, "desc": "لإمتلاك 50,000 نقطة"},
    "rich_2": {"name": "المليونير", "icon": "💸", "type": "points", "value": 100000, "desc": "لإمتلاك 100,000 نقطة"},

    # --- أوسمة تعتمد على مدة الانضمام ---
    "veteran_1": {"name": "المخضرم", "icon": "🎖️", "type": "days", "value": 30, "desc": "لمرور 30 يوماً على الانضمام"},
    "veteran_2": {"name": "الأسطورة", "icon": "🏆", "type": "days", "value": 90, "desc": "لمرور 90 يوماً على الانضمام"},
}


@client.on(events.NewMessage(func=lambda e: not e.is_private and e.sender and not e.sender.bot))
async def check_achievements_handler(event):
    """
    This handler runs in the background with every message to check if a user
    has unlocked a new achievement.
    """
    if not await check_activation(event.chat_id): return
    
    session_updated = False
    
    async with AsyncDBSession() as session:
        # جلب بيانات المستخدم من قاعدة البيانات الجديدة
        user_obj = await get_or_create_user(session, event.chat_id, event.sender_id)
        
        # التأكد من وجود قائمة الأوسمة للمستخدم
        user_achievements = user_obj.achievements or []
        newly_unlocked = []

        # المرور على كل الإنجازات المتاحة
        for achievement_key, details in ACHIEVEMENTS.items():
            # التحقق إذا كان المستخدم لا يملك هذا الوسام بالفعل
            if achievement_key not in user_achievements:
                unlocked = False
                # التحقق من شرط الوسام
                try:
                    if details["type"] == "messages":
                        if user_obj.msg_count >= details["value"]:
                            unlocked = True
                    
                    elif details["type"] == "points":
                        if user_obj.points >= details["value"]:
                            unlocked = True

                    elif details["type"] == "days":
                        join_date_str = user_obj.join_date
                        if join_date_str:
                            join_datetime = datetime.strptime(join_date_str, "%Y-%m-%d")
                            if (datetime.now() - join_datetime).days >= details["value"]:
                                unlocked = True
                except Exception as e:
                    print(f"Error checking achievement {achievement_key}: {e}")
                    continue

                # إذا تم تحقيق الشرط
                if unlocked:
                    newly_unlocked.append(achievement_key)
                    session_updated = True
                    
                    # إرسال تهنئة في المجموعة
                    user_mention = f"[{event.sender.first_name}](tg://user?id={event.sender.id})"
                    achievement_name = f"**{details['name']} {details['icon']}**"
                    
                    await event.reply(
                        f"**🎉 | تهانينا {user_mention}!**\n\n"
                        f"**لقد حصلت على وسام {achievement_name}**\n"
                        f"**السبب:** **{details['desc']}**"
                    )

        # حفظ التغييرات في قاعدة البيانات مرة واحدة فقط إذا تم فتح أي وسام
        if session_updated:
            user_obj.achievements = user_achievements + newly_unlocked
            flag_modified(user_obj, "achievements")
            await session.commit()
