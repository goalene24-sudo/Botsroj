import os
# (تم التعديل) استيراد المكتبات الغير متزامنة
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import logging

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- إعدادات قاعدة البيانات ---
DB_NAME = "surooj.db"
# (تم التعديل) استخدام محرك aiosqlite للعمل الغير متزامن
DB_URI = f"sqlite+aiosqlite:///{DB_NAME}?check_same_thread=False"  # إضافة check_same_thread=False لتجنب أخطاء SQLite

# --- تهيئة SQLAlchemy (بطريقة غير متزامنة) ---
# (تم التعديل) إنشاء محرك غير متزامن مع التحقق من النجاح
try:
    engine = create_async_engine(DB_URI, echo=True, poolclass=NullPool)  # استخدام NullPool لتجنب مشكلة e3q8
    logger.info(f"تم تهيئة المحرك بنجاح لـ {DB_URI}")
except Exception as e:
    logger.critical(f"فشل تهيئة المحرك: {e}", exc_info=True)
    raise

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
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("تم إنشاء الجداول بنجاح (chats, users, vips, etc.).")
    except Exception as e:
        logger.error(f"فشل إنشاء الجداول: {e}", exc_info=True)
        raise

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل إعدادات قاعدة البيانات SQLAlchemy (الغير متزامنة) بنجاح. <<")
