# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# --- إعدادات قاعدة البيانات ---

# اسم ملف قاعدة البيانات. SQLite هو خيار بسيط ومثالي ومناسب لاستضافة Railway
DB_NAME = "surooj.db"
DB_URI = f"sqlite:///{DB_NAME}"

# --- تهيئة SQLAlchemy ---

# إنشاء "المحرك" الذي يتصل بقاعدة البيانات
# connect_args={'check_same_thread': False} ضروري لـ SQLite مع البوتات
engine = create_engine(DB_URI, connect_args={'check_same_thread': False})

# إنشاء "جلسة" (Session) للتحدث مع قاعدة البيانات
# scoped_session تضمن أن كل مستخدم يحصل على جلسة خاصة به لمنع تداخل البيانات
session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
SESSION = scoped_session(session_factory)

# إنشاء "الأساس" (Base) الذي سترث منه كل جداولنا (نماذج البيانات)
Base = declarative_base()
Base.query = SESSION.query_property()

def init_db():
    """
    يقوم بإنشاء جميع الجداول في قاعدة البيانات إذا لم تكن موجودة.
    """
    # استيراد جميع النماذج هنا لتسجيلها في Base
    # (سنضيف النماذج لاحقًا في المراحل القادمة)
    # import models
    Base.metadata.create_all(bind=engine)

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل إعدادات قاعدة البيانات SQLAlchemy بنجاح. <<")
