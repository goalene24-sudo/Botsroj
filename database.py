# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# --- إعدادات قاعدة البيانات ---
DB_NAME = "surooj.db"
DB_URI = f"sqlite:///{DB_NAME}"

# --- تهيئة SQLAlchemy ---
engine = create_engine(DB_URI, connect_args={'check_same_thread': False})
session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
SESSION = scoped_session(session_factory)

Base = declarative_base()
Base.query = SESSION.query_property()

def init_db():
    """
    يقوم بإنشاء جميع الجداول في قاعدة البيانات إذا لم تكن موجودة.
    """
    # --- (تم التعديل هنا) ---
    # استيراد النماذج من ملف models.py لجعلها معروفة لـ SQLAlchemy
    import models
    Base.metadata.create_all(bind=engine)

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل إعدادات قاعدة البيانات SQLAlchemy بنجاح. <<")
