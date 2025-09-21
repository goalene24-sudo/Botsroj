import json
import logging
from telethon import Button
import config
from datetime import datetime
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin
from telethon.errors import ChatAdminRequiredError
from telethon.errors.rpcerrorlist import UserNotParticipantError, ChannelPrivateError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import IntegrityError

# --- استيراد كل مكونات قاعدة البيانات هنا ---
from sqlalchemy.future import select
# --- (تم التعديل هنا) استيراد الوحدة كاملة بدلاً من متغير واحد ---
import database
from models import (
    User, Vip, SecondaryDev, Creator, BotAdmin, Chat,  
    CommandSetting, Lock, CustomCommand, GlobalSetting
)
# --- استيراد البيانات الجديدة من الملف المنفصل ---
from .fun_data import JOKES, RIDDLES

logger = logging.getLogger(__name__)

# --- دوال الإعدادات العامة ---
async def get_global_setting(key, default=None):
    async with database.AsyncDBSession() as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting and setting.value:
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                return setting.value
        return default

async def set_global_setting(key, value):
    async with database.AsyncDBSession() as session:
        if isinstance(value, (dict, list)):
            value_to_store = json.dumps(value, ensure_ascii=False)
        else:
            value_to_store = str(value)

        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value_to_store
        else:
            new_setting = GlobalSetting(key=key, value=value_to_store)
            session.add(new_setting)
        await session.commit()

# --- دوال مساعدة مركزية ---
async def get_or_create_chat(session, chat_id):
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
    result = await session.execute(
        select(User).where(User.chat_id == chat_id, User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    else:
        try:
            user = User(chat_id=chat_id, user_id=user_id)
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user
        except IntegrityError:
            logger.warning(f"Race condition detected for user {user_id} in chat {chat_id}. Rolling back.")
            await session.rollback()
            result = await session.execute(
                select(User).where(User.chat_id == chat_id, User.user_id == user_id)
            )
            return result.scalar_one_or_none()

# --- تعريف مستويات الرتب ---
class Ranks:
    MEMBER, VIP, MOD, ADMIN, CREATOR, OWNER, SECONDARY_DEV, MAIN_DEV = range(8)

try:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    GEMINI_ENABLED = True
    print(">> تم تفعيل الذكاء الاصطناعي Gemini بنجاح.")
except (ImportError, AttributeError):
    print(">> تحذير: مكتبة Gemini غير مثبتة أو لم يتم العثور على المفتاح. ميزات الذكاء الاصطناعي ستكون معطلة.")
    GEMINI_ENABLED = False

# --- متغيرات وقت التشغيل (لا تحتاج قاعدة بيانات) ---
RPS_GAMES, XO_GAMES, FLOOD_TRACKER, BLESS_COUNTERS, KICKED_CHATS = {}, {}, {}, {}, set()
QUOTES = [ "اي والله صدك.", "هذا الحچي المعدل.", "مافتهمت بس مبين قافل." ]

def get_rank_name(rank_level):
    ranks_map = {
        Ranks.MAIN_DEV: "المطور الرئيسي",
        Ranks.SECONDARY_DEV: "مطور ثانوي",
        Ranks.OWNER: "مالك المجموعة",
        Ranks.CREATOR: "منشئ",
        Ranks.ADMIN: "ادمن",
        Ranks.MOD: "مشرف",
        Ranks.VIP: "عضو مميز"
    }
    return ranks_map.get(rank_level, "عضو")

async def is_admin(client, chat_id, user_id):
    if not isinstance(chat_id, int) or chat_id > 0:
        return False
    try:
        perms = await client.get_permissions(chat_id, user_id)
        if perms.is_creator or perms.is_admin or perms.ban_users or perms.add_admins:
            return True
    except (UserNotParticipantError, ChatAdminRequiredError, ValueError, ChannelPrivateError):
        return False
    except Exception as e:
        logger.error(f"Error in is_admin for user {user_id} in chat {chat_id}: {e}")
        return False
    return False

async def get_user_rank(client, user_id, chat_id):
    if user_id in config.SUDO_USERS:
        return Ranks.MAIN_DEV

    async with database.AsyncDBSession() as session:
        is_secondary_dev = await session.execute(select(SecondaryDev).where(SecondaryDev.chat_id == chat_id, SecondaryDev.user_id == user_id))
        if is_secondary_dev.scalar_one_or_none():
            return Ranks.SECONDARY_DEV

    try:
        perms = await client.get_permissions(chat_id, user_id)
        if perms.is_creator:
            return Ranks.OWNER
    except Exception:
        pass

    async with database.AsyncDBSession() as session:
        is_creator = await session.execute(select(Creator).where(Creator.chat_id == chat_id, Creator.user_id == user_id))
        if is_creator.scalar_one_or_none():
            return Ranks.CREATOR
        
        is_admin_db = await session.execute(select(BotAdmin).where(BotAdmin.chat_id == chat_id, BotAdmin.user_id == user_id))
        if is_admin_db.scalar_one_or_none():
            return Ranks.ADMIN

    if await is_admin(client, chat_id, user_id):
        return Ranks.MOD
    
    async with database.AsyncDBSession() as session:
        is_vip = await session.execute(select(Vip).where(Vip.chat_id == chat_id, Vip.user_id == user_id))
        if is_vip.scalar_one_or_none():
            return Ranks.VIP

    return Ranks.MEMBER

def get_uptime_string(start_time):
    uptime_delta = datetime.now() - start_time
    days = uptime_delta.days
    hours, rem = divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    
    parts = []
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
    
    custom_commands_dict = await get_global_setting("custom_commands", {})
    
    custom_buttons_row = []
    if custom_commands_dict:
        for name, data in custom_commands_dict.items():
            if "button_text" in data and data["button_text"]:
                button = Button.inline(data["button_text"], data=f"custom_cmd:{name}")
                custom_buttons_row.append(button)

    if custom_buttons_row:
        for i in range(0, len(custom_buttons_row), 2):
            buttons.append(custom_buttons_row[i:i + 2])
            
    return buttons

LOCK_TYPES = { "الصور": "photo", "الفيديو": "video", "المتحركة": "gif", "الملصقات": "sticker", "الروابط": "url", "المعرفات": "username", "التوجيه": "forward", "البوتات": "bot", "التكرار": "anti_flood" }
PERCENT_COMMANDS = [ "نسبة الحب", "نسبة الكره", "نسبة الجمال", "نسبة الغباء", "نسبة الخيانة", "نسبة الشجاعة", "نسبة الذكاء" ]
GAME_COMMANDS = ["نكتة", "حزورة", "كت", "حجره ورقه مقص", "xo", "الترتيب", "زواج", "كويز", "تخمين", "سمايلات", "سمايل", "سجلي", "المختلف", "اعلام الدول", "عواصم الدول", "رياضيات", "العكس", "اكمل المثل", "محيبس"]
ADMIN_COMMANDS = [ "القوانين", "تعديل القوانين", "ضع ترحيب", "حظر", "كتم", "الغاء الحظر", "الغاء الكتم", "رفع مشرف", "تنزيل مشرف", "رفع ادمن", "تنزيل ادمن", "الادمنيه", "تحذير", "حذف التحذيرات" ]

async def is_command_enabled(chat_id, command_key):
    async with database.AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        return (chat.settings or {}).get(command_key, True)

async def has_bot_permission(client, event):
    rank = await get_user_rank(client, event.sender_id, event.chat_id)
    return rank >= Ranks.MOD

async def check_activation(chat_id):
    async with database.AsyncDBSession() as session:
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        group = result.scalar_one_or_none()
        return group.is_active if group else False

async def add_points(chat_id, user_id, points_to_add):
    async with database.AsyncDBSession() as session:
        user = await get_or_create_user(session, chat_id, user_id)
        user.points = (user.points or 0) + points_to_add
        await session.commit()

async def build_protection_menu(chat_id):
    buttons, row = [], []
    async with database.AsyncDBSession() as session:
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
