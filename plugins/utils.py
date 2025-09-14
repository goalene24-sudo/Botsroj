import json
from telethon import Button
import config
from bot import client
from datetime import datetime
from telethon.tl.types import ChannelParticipantCreator
from telethon.errors import ChatAdminRequiredError
from telethon.errors.rpcerrorlist import UserNotParticipantError
from sqlalchemy.orm.attributes import flag_modified
import logging

# --- استيراد كل مكونات قاعدة البيانات هنا ---
from sqlalchemy.future import select
from database import AsyncDBSession
from models import (
    User, Vip, SecondaryDev, Creator, BotAdmin, Chat,    
    CommandSetting, Lock, GlobalSetting
)

logger = logging.getLogger(__name__)

# --- دوال مساعدة مركزية ---
async def get_or_create_chat(session, chat_id):
    """الحصول على مجموعة من قاعدة البيانات أو إنشائها مع تهيئة الحقول."""
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(
            id=chat_id,    
            settings={},    
            lock_settings={},
            filtered_words=[],
            custom_replies={}
        )
        session.add(chat)
        await session.flush()
        await session.refresh(chat)
    return chat

async def get_or_create_user(session, chat_id, user_id):
    """الحصول على مستخدم من قاعدة البيانات أو إنشائه إذا لم يكن موجودًا."""
    result = await session.execute(
        select(User).where(User.chat_id == chat_id, User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(chat_id=chat_id, user_id=user_id)
        session.add(user)
        await session.flush()
        await session.refresh(user)
    return user

async def get_global_setting(key, default=None):
    """جلب قيمة إعداد عام من قاعدة البيانات."""
    async with AsyncDBSession() as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting and setting.value:
            try:
                return json.loads(setting.value)
            except (json.JSONDecodeError, TypeError):
                return setting.value
        return default

# --- تعريف مستويات الرتب ---
class Ranks:
    MEMBER = 0
    VIP = 1
    MOD = 2
    ADMIN = 3
    CREATOR = 4
    OWNER = 5
    SECONDARY_DEV = 6
    MAIN_DEV = 7

try:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    GEMINI_ENABLED = True
    print(">> تم تفعيل الذكاء الاصطناعي Gemini بنجاح.")
except (ImportError, AttributeError):
    print(">> تحذير: مكتبة Gemini غير مثبتة أو لم يتم العثور على المفتاح.")
    GEMINI_ENABLED = False

# --- متغيرات وقت التشغيل ---
RPS_GAMES = {} # <-- (تمت إعادة السطر المفقود هنا)
XO_GAMES = {}
FLOOD_TRACKER = {}

# --- قوائم ثابتة ---
PERCENT_COMMANDS = [ "نسبة الحب", "نسبة الكره", "نسبة الجمال", "نسبة الغباء", "نسبة الخيانة", "نسبة الشجاعة", "نسبة الذكاء" ]
GAME_COMMANDS = ["نكتة", "حزورة", "كت", "حجره ورقه مقص", "xo", "الترتيب", "زواج", "كويز", "تخمين", "سمايلات", "سمايل", "سجلي", "المختلف", "اعلام الدول", "عواصم الدول", "رياضيات", "العكس", "اكمل المثل", "محيبس"]
ADMIN_COMMANDS = [ "القوانين", "تعديل القوانين", "ضع ترحيب", "حظر", "كتم", "الغاء الحظر", "الغاء الكتم", "رفع مشرف", "تنزيل مشرف", "رفع ادمن", "تنزيل ادمن", "الادمنيه", "تحذير", "حذف التحذيرات" ]

def get_rank_name(rank_level):
    if rank_level == Ranks.MAIN_DEV: return "المطور الرئيسي"
    elif rank_level == Ranks.SECONDARY_DEV: return "مطور ثانوي"
    elif rank_level == Ranks.OWNER: return "مالك المجموعة"
    elif rank_level == Ranks.CREATOR: return "منشئ"
    elif rank_level == Ranks.ADMIN: return "ادمن"
    elif rank_level == Ranks.MOD: return "مشرف"
    elif rank_level == Ranks.VIP: return "عضو مميز"
    else: return "عضو"

async def get_user_rank(user_id, chat_id):
    if user_id in config.SUDO_USERS: return Ranks.MAIN_DEV
    async with AsyncDBSession() as session:
        if (await session.execute(select(SecondaryDev).where(SecondaryDev.chat_id == chat_id, SecondaryDev.user_id == user_id))).scalar_one_or_none(): return Ranks.SECONDARY_DEV
    try:
        participant = await client.get_participant(chat_id, user_id)
        if isinstance(participant, ChannelParticipantCreator): return Ranks.OWNER
    except UserNotParticipantError: pass
    except Exception: pass
    async with AsyncDBSession() as session:
        if (await session.execute(select(Creator).where(Creator.chat_id == chat_id, Creator.user_id == user_id))).scalar_one_or_none(): return Ranks.CREATOR
        if (await session.execute(select(BotAdmin).where(BotAdmin.chat_id == chat_id, BotAdmin.user_id == user_id))).scalar_one_or_none(): return Ranks.ADMIN
    try:
        perms = await client.get_permissions(chat_id, user_id)
        if perms.is_admin: return Ranks.MOD
    except (UserNotParticipantError, ChatAdminRequiredError): pass
    except Exception: pass
    async with AsyncDBSession() as session:
        if (await session.execute(select(Vip).where(Vip.chat_id == chat_id, Vip.user_id == user_id))).scalar_one_or_none(): return Ranks.VIP
    return Ranks.MEMBER

def get_uptime_string(start_time):
    uptime_delta, parts = datetime.now() - start_time, []
    days, hours, rem = uptime_delta.days, *divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0: parts.append(f"{days} يوم")
    if hours > 0: parts.append(f"{hours} ساعة")
    if minutes > 0: parts.append(f"{minutes} دقيقة")
    return " و ".join(parts) if parts else "بضع ثواني"

MAIN_MENU_MESSAGE = """- - - - - - - - - - - - - - - - - -
⚜️ **قائمة أوامر سُرُوچ الرئيسية** ⚜️
- - - - - - - - - - - - - - - - - -

هلا والله! 👋 آني سُـرُوچ، مساعدك الرقمي بالمجموعة.

اختر أحد الأقسام من القائمة أدناه: 👇"""

async def build_main_menu_buttons():
    buttons = [
        [Button.inline("م2 التفاعل 👥", data="social_menu"), Button.inline("م1 الالعاب 🎮", data="fun_menu")],
        [Button.inline("م4 المتجر 🛒", data="shop_menu"), Button.inline("م3 ملفي 👤", data="profile_menu")],
        [Button.inline("م6 الإدارة ⚙️", data="admin_hub:main"), Button.inline("م5 الادوات 🛠️", data="tools_menu")],
        [Button.inline("م8 الردود 💬", data="replies_menu"), Button.inline("م7 الدينيه 🕌", data="services_menu")],
        [Button.inline("م9 حول البوت ℹ️", data="about_menu")]
    ]
    custom_commands = await get_global_setting("custom_commands", {})
    custom_buttons_row = []
    if custom_commands:
        for name, data in custom_commands.items():
            if isinstance(data, dict) and data.get("button_text"):
                custom_buttons_row.append(Button.inline(data["button_text"], data=f"ccmd:{name}"))
    if custom_buttons_row:
        buttons.append([]) 
        for i in range(0, len(custom_buttons_row), 2):
            buttons.append(custom_buttons_row[i:i + 2])
    return buttons

LOCK_TYPES = { "الصور": "photo", "الفيديو": "video", "المتحركة": "gif", "الملصقات": "sticker", "الروابط": "url", "المعرفات": "username", "التوجيه": "forward", "البوتات": "bot", "التكرار": "anti_flood" }

async def is_command_enabled(chat_id, command_key):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        return (chat.settings or {}).get(command_key, True)

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
    async with AsyncDBSession() as session:
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        group = result.scalar_one_or_none()
        return group.is_active if group else True

async def add_points(chat_id, user_id, points_to_add):
    async with AsyncDBSession() as session:
        user = await get_or_create_user(session, chat_id, user_id)
        user.points = (user.points or 0) + points_to_add
        await session.commit()

async def build_protection_menu(chat_id):
    buttons, row = [], []
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        locks = chat.lock_settings or {}
    for name, key in LOCK_TYPES.items():
        is_locked = locks.get(key, False)
        emoji = "🔒" if is_locked else "🔓"
        row.append(Button.inline(f"{emoji} {name}", data=f"toggle_lock:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    return buttons

def build_xo_keyboard(board, game_over=False):
    buttons = []
    for i in range(0, 9, 3):
        row = []
        for j in range(i, i + 3):
            text = board[j] if board[j] != '-' else ' '
            callback_data = "xo:done" if game_over else f"xo:{j}"
            row.append(Button.inline(text, data=callback_data))
        buttons.append(row)
    return buttons

def check_xo_winner(board):
    lines = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in lines:
        if board[a] == board[b] == board[c] != '-': return board[a]
    return 'draw' if '-' not in board else None
