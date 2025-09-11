import os
import sys
import logging

# إعداد اللوجر لإظهار الأخطاء الحرجة
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s'
)
LOGGER = logging.getLogger(__name__)

API_ID = os.environ.get("API_ID", None)
API_HASH = os.environ.get("API_HASH", None)
BOT_TOKEN = os.environ.get("BOT_TOKEN", None)

# التحقق من وجود المتغيرات الأساسية
if not all([API_ID, API_HASH, BOT_TOKEN]):
    LOGGER.critical("أحد المتغيرات المطلوبة (API_ID, API_HASH, BOT_TOKEN) مفقود. يرجى إضافتها في قسم Variables في Railway.")
    sys.exit(1) # إيقاف البوت بشكل صحيح

# محاولة تحويل API_ID إلى رقم
try:
    API_ID = int(API_ID)
except ValueError:
    LOGGER.critical("قيمة API_ID يجب أن تكون رقماً صحيحاً.")
    sys.exit(1)

# --- بقية المتغيرات ---
sudo_users_str = os.environ.get("SUDO_USERS", "").split(',')
SUDO_USERS = [int(user_id) for user_id in sudo_users_str if user_id]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- (تمت الإضافة) متغيرات بحث جوجل ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", None)
GOOGLE_CX_ID = os.environ.get("GOOGLE_CX_ID", None)


LOGGER.info(">> تم تحميل متغيرات الإعدادات بنجاح. <<")
