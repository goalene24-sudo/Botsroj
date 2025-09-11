# migrate_db.py

import json
import os
from database import SESSION, init_db
from models import Chat, User, Alias, MessageHistory

# اسم ملف قاعدة البيانات القديم
OLD_DB_FILE = "database.json"

def migrate_data():
    """
    الدالة الرئيسية التي تقوم بقراءة البيانات القديمة وترحيلها.
    """
    print(">> [المرحلة 1/4] بدء عملية ترحيل البيانات...")

    # التأكد من وجود الملف القديم
    if not os.path.exists(OLD_DB_FILE):
        print(f"** خطأ: لم يتم العثور على ملف '{OLD_DB_FILE}'. لا توجد بيانات لترحيلها.")
        return

    # أولاً، نقوم بإنشاء الجداول في قاعدة البيانات الجديدة
    print(">> [المرحلة 2/4] إنشاء الجداول في قاعدة البيانات الجديدة (surooj.db)...")
    init_db()
    print(">> الجداول تم إنشاؤها بنجاح.")

    # ثانياً، نقوم بقراءة البيانات من ملف JSON القديم
    try:
        with open(OLD_DB_FILE, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        print(f">> [المرحلة 3/4] تم قراءة البيانات من '{OLD_DB_FILE}' بنجاح.")
    except Exception as e:
        print(f"** خطأ فادح أثناء قراءة ملف JSON: {e}")
        return

    # ثالثاً، نبدأ عملية الترحيل
    print(">> [المرحلة 4/4] جاري نقل البيانات إلى الجداول الجديدة...")
    
    chats_added = 0
    users_added = 0
    aliases_added = 0
    history_added = 0

    # المرور على كل مجموعة في البيانات القديمة
    for chat_id_str, chat_data in old_data.items():
        # تخطي أي بيانات لا تبدو كمعرف مجموعة
        if not chat_id_str.startswith('-'):
            continue

        chat_id = int(chat_id_str)
        
        # إنشاء سجل جديد للمجموعة في جدول Chats
        new_chat = Chat(
            id=chat_id,
            total_msgs=chat_data.get("total_msgs", 0),
            last_dhikr_time=chat_data.get("last_dhikr_time", 0)
        )
        SESSION.add(new_chat)
        chats_added += 1

        # ترحيل المستخدمين التابعين لهذه المجموعة
        if "users" in chat_data:
            for user_id_str, user_data in chat_data["users"].items():
                new_user = User(
                    user_id=int(user_id_str),
                    chat_id=chat_id,
                    msg_count=user_data.get("msg_count", 0),
                    points=user_data.get("points", 0),
                    sahaqat=user_data.get("sahaqat", 0),
                    join_date=user_data.get("join_date"),
                    achievements=user_data.get("achievements", []),
                    inventory=user_data.get("inventory", {})
                )
                SESSION.add(new_user)
                users_added += 1

        # ترحيل الاختصارات
        if "command_aliases" in chat_data:
            for alias_name, command_name in chat_data["command_aliases"].items():
                new_alias = Alias(
                    chat_id=chat_id,
                    alias_name=alias_name,
                    command_name=command_name
                )
                SESSION.add(new_alias)
                aliases_added += 1
        
        # ترحيل سجل الرسائل
        if "message_history" in chat_data:
            for msg_item in chat_data["message_history"]:
                new_msg = MessageHistory(
                    chat_id=chat_id,
                    msg_id=msg_item.get("msg_id"),
                    msg_type=msg_item.get("type")
                )
                SESSION.add(new_msg)
                history_added += 1

    # رابعاً، حفظ كل التغييرات في قاعدة البيانات
    try:
        SESSION.commit()
        print("\n\n✅ --- تمت عملية الترحيل بنجاح! --- ✅")
        print(f"สรุป: تم إضافة {chats_added} مجموعة، {users_added} مستخدم، {aliases_added} اختصار، و {history_added} رسالة في السجل.")
        print("يمكنك الآن الانتقال إلى المرحلة التالية لتحديث كود البوت.")
    except Exception as e:
        print(f"** خطأ فادح أثناء حفظ البيانات في قاعدة البيانات الجديدة: {e}")
        SESSION.rollback() # التراجع عن أي تغييرات في حال حدوث خطأ
    finally:
        SESSION.close()

# --- نقطة انطلاق السكريبت ---
if __name__ == "__main__":
    migrate_data()