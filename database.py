import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# --- إعدادات قاعدة البيانات ---
DB_NAME = "surooj.db"
# استخدام محرك aiosqlite للعمل الغير متزامن
DB_URI = f"sqlite+aiosqlite:///{DB_NAME}?check_same_thread=False"

# --- تهيئة SQLAlchemy (بطريقة غير متزامنة) ---
# (تم التعديل) تغيير echo إلى False لإيقاف طباعة كل استعلام
engine = create_async_engine(DB_URI, echo=False, poolclass=NullPool)

# إنشاء مُصنِّع جلسات غير متزامن
# expire_on_commit=False مهم للتعامل مع البوتات لتجنب أخطاء الوصول للكائنات بعد إغلاق الجلسة
AsyncDBSession = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()

# دالة لإنشاء الجداول
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
