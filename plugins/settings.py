# plugins/settings.py
from telethon import events, Button
from bot import client
from .utils import check_activation, Ranks, get_user_rank, db, save_db

# --- (جديد) قائمة الإعدادات القابلة للتفعيل والتعطيل ---
# المفتاح هو الاسم الذي سيظهر، والقيمة هي مفتاح الحفظ في قاعدة البيانات
TOGGLEABLE_SETTINGS = {
    "الترحيب": "welcome_enabled",
    "الردود العامة": "public_replies_enabled",
    "الألعاب": "games_enabled",
    "الأيدي": "id_enabled",
    "الأوامر الاجتماعية": "social_commands_enabled",
}

async def build_settings_menu(chat_id):
    """دالة لإنشاء قائمة أزرار الإعدادات بشكل ديناميكي."""
    chat_id_str = str(chat_id)
    settings = db.get(chat_id_str, {}).get("command_settings", {})
    buttons = []
    
    # بناء الأزرار بشكل زوجي
    row = []
    for display_name, db_key in TOGGLEABLE_SETTINGS.items():
        # القيمة الافتراضية هي "مفعل" إذا لم يتم تحديدها من قبل
        is_enabled = settings.get(db_key, True)
        
        if is_enabled:
            # إذا كانت الميزة مفعلة، أظهر زر "تعطيل"
            button = Button.inline(f"✅ {display_name}", data=f"settings:toggle:{db_key}")
        else:
            # إذا كانت الميزة معطلة، أظهر زر "تفعيل"
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
    
    user_rank = await get_user_rank(event.sender_id, event)
    # فقط الأدمن فما فوق يمكنهم تغيير الإعدادات
    if user_rank < Ranks.BOT_ADMIN:
        return await event.answer("🚫 | **هذا القسم مخصص للأدمنية فما فوق.**", alert=True)

    chat_id_str = str(event.chat_id)
    data_parts = event.data.decode().split(':')
    action = data_parts[1]

    if action == "main":
        keyboard = await build_settings_menu(event.chat_id)
        text = "**⚙️ | إعدادات تفعيل وتعطيل الأوامر**\n\n**اضغط على أي زر لتغيير حالته:**"
        await event.edit(text, buttons=keyboard)

    elif action == "toggle":
        setting_key = data_parts[2]
        
        # التأكد من وجود قسم الإعدادات في قاعدة البيانات
        if "command_settings" not in db.get(chat_id_str, {}):
            db.setdefault(chat_id_str, {})["command_settings"] = {}

        # تغيير الحالة (عكسها)
        current_state = db[chat_id_str]["command_settings"].get(setting_key, True)
        db[chat_id_str]["command_settings"][setting_key] = not current_state
        save_db(db)
        
        # إعادة بناء القائمة بالحالة الجديدة
        keyboard = await build_settings_menu(event.chat_id)
        await event.edit(buttons=keyboard)
        display_name = [k for k, v in TOGGLEABLE_SETTINGS.items() if v == setting_key][0]
        await event.answer(f"✅ | **تم {'تعطيل' if current_state else 'تفعيل'} {display_name} بنجاح.**")