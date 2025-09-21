import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# سيتم تعريف هذا المتغير لاحقاً من __main__.py
# يجب أن يبقى هنا حتى لا تتعطل بقية الملفات التي تستورده
AsyncDBSession = None

Base = declarative_base()

# --- (تم التعديل هنا) الدالة الآن تستقبل المحرك كوسيط ---
async def init_db(engine):
    """
    يقوم بإنشاء جميع الجداول في قاعدة البيانات إذا لم تكن موجودة.
    """
    # استيراد النماذج هنا لتجنب الاستيراد الدائري
    import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل إعدادات قاعدة البيانات SQLAlchemy (الغير متزامنة) بنجاح. <<")
