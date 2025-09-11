# database.py

import os
# (تم التعديل) استيراد المكتبات الغير متزامنة
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# --- إعدادات قاعدة البيانات ---
DB_NAME = "surooj.db"
# (تم التعديل) استخدام محرك aiosqlite للعمل الغير متزامن
DB_URI = f"sqlite+aiosqlite:///{DB_NAME}"

# --- تهيئة SQLAlchemy (بطريقة غير متزامنة) ---
# (تم التعديل) إنشاء محرك غير متزامن
engine = create_async_engine(DB_URI)

# (تم التعديل) إنشاء مُصنِّع جلسات غير متزامن
# expire_on_commit=False مهم للتعامل مع البوتات لتجنب أخطاء الوصول للكائنات بعد إغلاق الجلسة
AsyncDBSession = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()

# (تم التعديل) تحويل الدالة إلى غير متزامنة
async def init_db():
    """
    يقوم بإنشاء جميع الجداول في قاعدة البيانات إذا لم تكن موجودة.
    """
    # استيراد النماذج هنا لتجنب الاستيراد الدائري
    import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل إعدادات قاعدة البيانات SQLAlchemy (الغير متزامنة) بنجاح. <<")
