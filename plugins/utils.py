# plugins/utils.py

import json
from telethon import Button
import config
from bot import client
from datetime import datetime
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin, ChannelParticipantsAdmins
from telethon.errors import ChatAdminRequiredError
from telethon.errors.rpcerrorlist import UserNotParticipantError

# --- (مُصحَّح) تعريف مستويات الرتب مع إعادة رتبة المالك ---
class Ranks:
    MEMBER = 0        # عضو
    VIP = 1           # عضو مميز
    MOD = 2           # مشرف (من صلاحيات المجموعة)
    ADMIN = 3         # ادمن (من صلاحيات البوت)
    CREATOR = 4       # المنشئ (تمت ترقيته)
    OWNER = 5         # مالك المجموعة الفعلي
    SECONDARY_DEV = 6 # مطور ثانوي
    MAIN_DEV = 7      # المطور الرئيسي

try:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    GEMINI_ENABLED = True
    print(">> تم تفعيل الذكاء الاصطناعي Gemini بنجاح.")
except (ImportError, AttributeError):
    print(">> تحذير: مكتبة Gemini غير مثبتة أو لم يتم العثور على المفتاح. ميزات الذكاء الاصطناعي ستكون معطلة.")
    GEMINI_ENABLED = False

DB_FILE = "database.json"
RPS_GAMES = {}
XO_GAMES = {}
FLOOD_TRACKER = {}
BLESS_COUNTERS = {}

JOKES = [
    "اكو واحد راح للطبيب گاله دكتور عندي إسهال، الطبيب گاله حلّل، گال لعد شعبالك قابل مخثر؟",
    "فد يوم واحد گال لمرته: اليوم اريد اكل بره، مرته حطتله الاكل بالسطح."
]
RIDDLES = [
    ("شنو الشي اللي كلما تاخذ منه يكبر؟", "الحفرة"),
    ("شنو الشي اللي يمشي بلا رجلين ويبچي بلا عيون؟", "الغيمة")
]
QUOTES = [ "اي والله صدك.", "هذا الحچي المعدل.", "مافتهمت بس مبين قافل." ]

def load_db():
    try:
        with open("database.json", 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return {}

def save_db(data):
    with open("database.json", 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

def is_vip(chat_id, user_id):
    chat_id_str = str(chat_id)
    vips = db.get(chat_id_str, {}).get("vips", [])
    return user_id in vips

def is_secondary_dev(chat_id, user_id):
    chat_id_str = str(chat_id)
    secondary_devs = db.get(chat_id_str, {}).get("secondary_devs", [])
    return user_id in secondary_devs

# --- (مُصحَّح) دالة تحويل الرتبة إلى نص ---
def get_rank_name(rank_level):
    if rank_level == Ranks.MAIN_DEV: return "المطور الرئيسي"
    elif rank_level == Ranks.SECONDARY_DEV: return "مطور ثانوي"
    elif rank_level == Ranks.OWNER: return "مالك المجموعة"
    elif rank_level == Ranks.CREATOR: return "منشئ"
    elif rank_level == Ranks.ADMIN: return "ادمن"
    elif rank_level == Ranks.MOD: return "مشرف"
    elif rank_level == Ranks.VIP: return "عضو مميز"
    else: return "عضو"

# --- (مُصحَّح) دالة تحديد الرتبة ---
async def get_user_rank(user_id, chat_id):
    if user_id in config.SUDO_USERS:
        return Ranks.MAIN_DEV

    chat_id_str = str(chat_id)
    chat_data = db.get(chat_id_str, {})
    
    if user_id in chat_data.get("secondary_devs", []):
        return Ranks.SECONDARY_DEV

    try:
        participant = await client.get_participant(chat_id, user_id)
        if isinstance(participant, ChannelParticipantCreator):
            return Ranks.OWNER
    except UserNotParticipantError: pass
    except Exception: pass

    if user_id in chat_data.get("creators", []):
        return Ranks.CREATOR

    if user_id in chat_data.get("bot_admins", []):
        return Ranks.ADMIN

    try:
        perms = await client.get_permissions(chat_id, user_id)
        if perms.is_admin:
            return Ranks.MOD
    except (UserNotParticipantError, ChatAdminRequiredError): pass
    except Exception: pass
        
    if user_id in chat_data.get("vips", []):
        return Ranks.VIP

    return Ranks.MEMBER

def get_uptime_string(start_time):
    uptime_delta = datetime.now() - start_time
    days, hours, rem = uptime_delta.days, divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(rem[1], 60)
    uptime_str = ""
    if days > 0: uptime_str += f"{days} يوم و "
    if hours > 0: uptime_str += f"{hours} ساعة و "
    if minutes > 0: uptime_str += f"{minutes} دقيقة"
    return uptime_str.strip().strip('و ') or "بضع ثواني"

MAIN_MENU_MESSAGE = """- - - - - - - - - - - - - - - - - -
⚜️ **قائمة أوامر سُرُوچ الرئيسية** ⚜️
- - - - - - - - - - - - - - - - - -

هلا والله! 👋 آني سُـرُوچ، مساعدك الرقمي بالمجموعة.

اختر أحد الأقسام من القائمة أدناه: 👇"""

def build_main_menu_buttons():
    buttons = [
        [Button.inline("م2 التفاعل 👥", data="social_menu"), Button.inline("م1 الالعاب 🎮", data="fun_menu")],
        [Button.inline("م4 المتجر 🛒", data="shop_menu"), Button.inline("م3 ملفي 👤", data="profile_menu")],
        [Button.inline("م6 الإدارة ⚙️", data="admin_hub:main"), Button.inline("م5 الادوات 🛠️", data="tools_menu")],
        [Button.inline("م8 الردود 💬", data="replies_menu"), Button.inline("م7 الدينيه 🕌", data="services_menu")],
        [Button.inline("م9 حول البوت ℹ️", data="about_menu")]
    ]
    custom_commands = db.get("custom_commands", {})
    custom_buttons_row = [Button.inline(name.capitalize(), data=f"ccmd:{name}") for name, data in custom_commands.items() if data.get("show_button")]
    if custom_buttons_row:
        for i in range(0, len(custom_buttons_row), 2):
            buttons.append(custom_buttons_row[i:i + 2])
    return buttons

LOCK_TYPES = { "الصور": "photo", "الفيديو": "video", "المتحركة": "gif", "الملصقات": "sticker", "الروابط": "url", "المعرفات": "username", "التوجيه": "forward", "البوتات": "bot", "التكرار": "anti_flood" }
PERCENT_COMMANDS = [ "نسبة الحب", "نسبة الكره", "نسبة الجمال", "نسبة الغباء", "نسبة الخيانة", "نسبة الشجاعة", "نسبة الذكاء" ]
GAME_COMMANDS = ["نكتة", "حزورة", "كت", "حجره ورقه مقص", "xo", "الترتيب", "زواج", "كويز", "تخمين", "سمايلات", "سمايل", "سجلي", "المختلف", "اعلام الدول", "عواصم الدول", "رياضيات", "العكس", "اكمل المثل", "محيبس"]
ADMIN_COMMANDS = [ "القوانين", "تعديل القوانين", "ضع ترحيب", "حظر", "كتم", "الغاء الحظر", "الغاء الكتم", "رفع مشرف", "تنزيل مشرف", "رفع ادمن", "تنزيل ادمن", "الادمنيه", "تحذير", "حذف التحذيرات" ]

def is_command_enabled(chat_id, command_key):
    return db.get(str(chat_id), {}).get("command_settings", {}).get(command_key, True)

async def is_admin(chat_id, user_id):
    if chat_id < 0:
        try:
            p = await client.get_permissions(chat_id, user_id)
            return p.is_admin or p.is_creator
        except (UserNotParticipantError, ChatAdminRequiredError): return False
        except Exception: return False
    return False

async def has_bot_permission(event):
    rank = await get_user_rank(event.sender_id, event.chat_id)
    return rank >= Ranks.MOD

async def check_activation(chat_id):
    return not db.get(str(chat_id), {}).get("is_paused", False)

def add_points(chat_id, user_id, points_to_add):
    cid, uid = str(chat_id), str(user_id)
    db.setdefault(cid, {}).setdefault("users", {}).setdefault(uid, {"msg_count": 0, "sahaqat": 0, "points": 0})
    db[cid]["users"][uid]["points"] = db[cid]["users"][uid].get("points", 0) + points_to_add
    save_db(db)

async def build_protection_menu(chat_id):
    locks, buttons, row = db.get(str(chat_id), {}), [], []
    for name, key in LOCK_TYPES.items():
        emoji = "🔒" if locks.get(f"lock_{key}", False) else "🔓"
        row.append(Button.inline(f"{emoji} {name}", data=f"toggle_lock_{key}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    return buttons

# --- (تم التعديل) ---
def build_xo_keyboard(board, game_over=False):
    buttons = []
    for i in range(0, 9, 3):
        row = []
        for j in range(i, i + 3):
            text = board[j] if board[j] != '-' else ' '
            # --- (التغيير هنا) تعديل صيغة الـ data ---
            callback_data = "xo:done" if game_over else f"xo:{j}"
            row.append(Button.inline(text, data=callback_data))
        buttons.append(row)
    return buttons

def check_xo_winner(board):
    lines = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in lines:
        if board[a] == board[b] == board[c] != '-': return board[a]
    return 'draw' if '-' not in board else None
