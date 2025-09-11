# plugins/utils.py

import json
from telethon import Button
import config
from bot import client
from datetime import datetime
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin
from telethon.errors import ChatAdminRequiredError
from telethon.errors.rpcerrorlist import UserNotParticipantError

# --- (جديد) استيراد أدوات قاعدة البيانات ---
from database import SESSION
from models import Chat, User, GlobalSettings

# --- تعريف مستويات الرتب (لا تغيير هنا) ---
class Ranks:
    MEMBER = 0
    VIP = 1
    MOD = 2
    ADMIN = 3
    CREATOR = 4
    OWNER = 5
    SECONDARY_DEV = 6
    MAIN_DEV = 7

# --- (لا تغيير هنا) ---
try:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    GEMINI_ENABLED = True
    print(">> تم تفعيل الذكاء الاصطناعي Gemini بنجاح.")
except (ImportError, AttributeError):
    print(">> تحذير: مكتبة Gemini غير مثبتة أو لم يتم العثور على المفتاح. ميزات الذكاء الاصطناعي ستكون معطلة.")
    GEMINI_ENABLED = False

RPS_GAMES = {}
XO_GAMES = {}
FLOOD_TRACKER = {}
BLESS_COUNTERS = {}

JOKES = [
    "اكو واحد راح للطبيب گاله دكتور عندي إسهال، الطبيب گاله حلّل، گال لعد شعبالك قابل مخثر؟",
    "فد يوم واحد گال لمرته: اليوم اريد اكل بره، مرته حطتله الاكل بالسطح.",
]
RIDDLES = [
    ("شنو الشي اللي كلما تاخذ منه يكبر؟", "الحفرة"),
    ("شنو الشي اللي يمشي بلا رجلين ويبچي بلا عيون؟", "الغيمة"),
]
QUOTES = [ "اي والله صدك.", "هذا الحچي المعدل.", "مافتهمت بس مبين قافل." ]

# --- (جديد) دوال التعامل مع قاعدة البيانات ---

def get_or_create_chat(chat_id):
    """
    تجلب مجموعة من قاعدة البيانات أو تنشئها إذا لم تكن موجودة.
    """
    chat = SESSION.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        chat = Chat(id=chat_id)
        SESSION.add(chat)
        SESSION.commit()
    return chat

def get_or_create_user(chat_id, user_id):
    """
    تجلب مستخدمًا من قاعدة البيانات أو تنشئه إذا لم يكن موجودًا.
    """
    user = SESSION.query(User).filter(User.chat_id == chat_id, User.user_id == user_id).first()
    if not user:
        # نتأكد من وجود المجموعة أولاً
        get_or_create_chat(chat_id)
        user = User(chat_id=chat_id, user_id=user_id, join_date=datetime.now().strftime("%Y-%m-%d"))
        SESSION.add(user)
        SESSION.commit()
    return user

# --- (مُعدل بالكامل) الدوال القديمة تم تحديثها لتعمل مع SQLAlchemy ---

def is_vip(chat_id, user_id):
    user = get_or_create_user(chat_id, user_id)
    # لاحقًا، سنضيف منطق التحقق من المخزون هنا
    return user.rank >= Ranks.VIP

async def get_user_rank(user_id, chat_id):
    if user_id in config.SUDO_USERS:
        return Ranks.MAIN_DEV

    # أولاً، جلب رتبة المستخدم المخزنة في قاعدة البيانات
    db_user = get_or_create_user(chat_id, user_id)
    
    # ثانيًا، التحقق من الصلاحيات الحية في المجموعة (قد تتغير)
    try:
        participant = await client.get_participant(chat_id, user_id)
        if isinstance(participant, ChannelParticipantCreator):
            return Ranks.OWNER
        
        # إذا كان مشرفًا في المجموعة، نضمن أن رتبته على الأقل مشرف
        if isinstance(participant.participant, ChannelParticipantAdmin):
            if db_user.rank < Ranks.MOD:
                 return Ranks.MOD
    except (UserNotParticipantError, Exception):
        pass # المستخدم ليس في المجموعة أو لا توجد صلاحيات

    # إذا لم تكن هناك صلاحيات خاصة، نرجع الرتبة المخزنة
    return db_user.rank

def is_command_enabled(chat_id, command_key):
    chat = get_or_create_chat(chat_id)
    return chat.command_settings.get(command_key, True)

async def check_activation(chat_id):
    chat = get_or_create_chat(chat_id)
    return chat.is_active

def add_points(chat_id, user_id, points_to_add):
    user = get_or_create_user(chat_id, user_id)
    user.points += points_to_add
    SESSION.commit()

async def build_protection_menu(chat_id):
    chat = get_or_create_chat(chat_id)
    buttons, row = [], []
    LOCK_TYPES = { "الصور": "photo", "الفيديو": "video", "المتحركة": "gif", "الملصقات": "sticker" } # مثال مبسط
    for name, key in LOCK_TYPES.items():
        emoji = "🔒" if chat.lock_settings.get(f"lock_{key}", False) else "🔓"
        row.append(Button.inline(f"{emoji} {name}", data=f"toggle_lock_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    return buttons

# --- (دوال لم تتغير بعد) ---
def get_uptime_string(start_time):
    uptime_delta = datetime.now() - start_time
    days = uptime_delta.days
    hours, rem_seconds = divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(rem_seconds, 60)
    uptime_str = ""
    if days > 0: uptime_str += f"{days} يوم و "
    if hours > 0: uptime_str += f"{hours} ساعة و "
    if minutes > 0: uptime_str += f"{minutes} دقيقة"
    final_str = uptime_str.strip().strip('و ')
    return final_str if final_str else "بضع ثواني"

MAIN_MENU_MESSAGE = "..." # (محتوى القائمة كما هو)
def build_main_menu_buttons():
    # هذا سيتطلب تعديلاً لاحقًا لقراءة الأوامر المخصصة من قاعدة البيانات
    buttons = [
        [Button.inline("م2 التفاعل 👥", data="social_menu"), Button.inline("م1 الالعاب 🎮", data="fun_menu")],
    ]
    return buttons

def build_xo_keyboard(board, game_over=False):
    buttons = []
    for i in range(0, 9, 3):
        row = [Button.inline(board[j] if board[j] != '-' else ' ', data=f"xo:{j}" if not game_over else "xo:done") for j in range(i, i + 3)]
        buttons.append(row)
    return buttons
