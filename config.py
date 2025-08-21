# config.py
import os

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# تأكد من تحويل النص إلى قائمة من الأرقام
sudo_users_str = os.environ.get("SUDO_USERS", "").split(',')
SUDO_USERS = [int(user_id) for user_id in sudo_users_str if user_id]

# إذا كان لديك مفتاح Gemini API، أضفه كـ Secret أيضاً
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")