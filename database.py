import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# --- تعريف المتغيرات بشكل مبدئي ---
# سيتم تعيين قيمها الحقيقية لاحقاً من ملف __main__.py
engine = None
AsyncDBSession = None

Base = declarative_base()

# دالة لإنشاء الجداول
async def init_db():
    """
    يقوم بإنشاء جميع الجداول في قاعدة البيانات إذا لم تكن موجودة.
    """
    # استيراد النماذج هنا لتجنب الاستيراد الدائري
    import models
    # نستخدم المحرك العالمي الذي تم إنشاؤه في __main__.py
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل إعدادات قاعدة البيانات SQLAlchemy (الغير متزامنة) بنجاح. <<")
