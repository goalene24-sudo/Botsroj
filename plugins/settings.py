from telethon import events, Button
from bot import client

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
# (تم التعديل) استيراد الجلسة الغير متزامنة الجديدة
from database import AsyncDBSession
from models import Chat

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, Ranks, get_user_rank

# --- قائمة الإعدادات القابلة للتفعيل والتعطيل ---
TOGGLEABLE_SETTINGS = {
    "الترحيب": "welcome_enabled",
    "الردود العامة": "public_replies_enabled",
    "الألعاب": "games_enabled",
    "الأيدي": "id_enabled",
    "الأوامر الاجتماعية": "social_commands_enabled",
}


# --- دوال مساعدة جديدة لإدارة إعدادات المجموعة ---
async def get_chat_setting(chat_id, key, default=None):
    """تجلب إعدادًا معينًا من حقل الإعدادات للمجموعة."""
    async with AsyncDBSession() as session:
        # نبحث عن المجموعة باستخدام chat_id
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        # إذا كانت المجموعة موجودة ولديها إعدادات، نرجع القيمة المطلوبة
        if chat and chat.settings:
            return chat.settings.get(key, default)
        # إذا لم تكن موجودة، نرجع القيمة الافتراضية
        return default

async def set_chat_setting(chat_id, key, value):
    """تُعيّن إعدادًا معينًا في حقل الإعدادات للمجموعة."""
    from sqlalchemy.orm.attributes import flag_modified
    async with AsyncDBSession() as session:
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        
        # إذا لم تكن المجموعة موجودة في قاعدة البيانات، ننشئها
        if not chat:
            chat = Chat(id=chat_id, settings={})
            session.add(chat)
        
        # نأخذ نسخة قابلة للتعديل من الإعدادات الحالية
        new_settings = dict(chat.settings) if chat.settings else {}
        new_settings[key] = value
        chat.settings = new_settings # تحديث الإعدادات
        flag_modified(chat, "settings")
        
        await session.commit()


async def build_settings_menu(chat_id):
    """دالة لإنشاء قائمة أزرار الإعدادات بشكل ديناميكي من قاعدة البيانات."""
    buttons = []
    row = []
    
    # بناء الأزرار بشكل زوجي
    for display_name, db_key in TOGGLEABLE_SETTINGS.items():
        # القيمة الافتراضية هي "مفعل" (True) إذا لم يتم تحديدها من قبل
        is_enabled = await get_chat_setting(chat_id, db_key, True)
        
        if is_enabled:
            button = Button.inline(f"✅ {display_name}", data=f"settings:toggle:{db_key}")
        else:
            button = Button.inline(f"❌ {display_name}", data=f"settings:toggle:{db_key}")
        
        row.append(button)
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    # إضافة أي زر متبقي
    if row:
        buttons.append(row)
        
    buttons.append([Button.inline("🔙 رجوع إلى قائمة الإدارة", data="admin_hub:main")])
    return buttons

@client.on(events.CallbackQuery(pattern=b"settings:"))
async def settings_hub_handler(event):
    if not await check_activation(event.chat_id): return
    
    # --- (تم الإصلاح هنا) إضافة 'event.client' الناقص ---
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.ADMIN:
        return await event.answer("🚫 | **هذا القسم مخصص للادمنية فما فوق.**", alert=True)

    chat_id = event.chat_id
    data_parts = event.data.decode().split(':')
    action = data_parts[1]

    if action == "main":
        keyboard = await build_settings_menu(chat_id)
        text = "**⚙️ | إعدادات تفعيل وتعطيل الأوامر**\n\n**اضغط على أي زر لتغيير حالته:**"
        await event.edit(text, buttons=keyboard)

    elif action == "toggle":
        setting_key = data_parts[2]
        
        # جلب الحالة الحالية من قاعدة البيانات
        current_state = await get_chat_setting(chat_id, setting_key, True)
        
        # عكس الحالة وحفظها في قاعدة البيانات
        await set_chat_setting(chat_id, setting_key, not current_state)
        
        # إعادة بناء القائمة بالحالة الجديدة
        keyboard = await build_settings_menu(chat_id)
        await event.edit(buttons=keyboard)
        
        display_name = [k for k, v in TOGGLEABLE_SETTINGS.items() if v == setting_key][0]
        status_text = 'تعطيل' if current_state else 'تفعيل'
        await event.answer(f"✅ | **تم {status_text} {display_name} بنجاح.**")
