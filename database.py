import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# ===================================================================
# | START OF MODIFIED CODE | بداية الكود المعدل                      |
# ===================================================================

# --- البحث عن رابط قاعدة البيانات الخارجية (من Koyeb) ---
db_url = os.environ.get("DATABASE_URL")

# التحقق إذا كان الرابط موجوداً وخاص بـ PostgreSQL
if db_url and db_url.startswith("postgresql://"):
    # تحويل الرابط ليتوافق مع مكتبة asyncpg
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(">> تم العثور على قاعدة بيانات PostgreSQL. جاري الاتصال... <<")
    # إنشاء المحرك بدون poolclass لأنه غير ضروري مع PostgreSQL في هذه الحالة
    engine = create_async_engine(db_url, echo=False)
else:
    # --- في حال عدم وجود رابط خارجي، العودة لاستخدام الملف المحلي SQLite ---
    print(">> لم يتم العثور على قاعدة بيانات خارجية. سيتم استخدام ملف SQLite المحلي. <<")
    DB_NAME = "surooj.db"
    DB_URI = f"sqlite+aiosqlite:///{DB_NAME}?check_same_thread=False"
    engine = create_async_engine(DB_URI, echo=False, poolclass=NullPool)

# ===================================================================
# | END OF MODIFIED CODE | نهاية الكود المعدل                        |
# ===================================================================

# إنشاء مُصنِّع جلسات غير متزامن
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
