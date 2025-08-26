# plugins/admin_menus.py
from telethon import events, Button
from bot import client
from .utils import check_activation, Ranks, get_user_rank, build_protection_menu

# --- نصوص قوائم الأوامر الجديدة ---

OWNER_COMMANDS_TEXT = """**👑 أوامر المالك**

**- رفع منشئ:** (بالرد) لترقية عضو إلى رتبة منشئ.
**- تنزيل منشئ:** (بالرد) لعزل عضو من رتبة المنشئ.
**- المنشئين:** لعرض قائمة المنشئين في المجموعة.
**- مسح المنشئين:** لحذف جميع المنشئين في المجموعة.
**- رفع مالك:** (بالرد) يمكن للمالك رفع نفسه مالك بالبوت اذا كان عضو.
"""

CREATOR_COMMANDS_TEXT = """**⚜️ أوامر المنشئ**

**- رفع ادمن:** (بالرد) لترقية عضو إلى رتبة أدمن في البوت.
**- تنزيل ادمن:** (بالرد) لعزل عضو من رتبة الأدمن.
**- الادمنيه:** لعرض قائمة الأدمنية في البوت.
**- مسح كل الادمنيه:** لحذف جميع أدمنية البوت في المجموعة.
"""

BOT_ADMIN_COMMANDS_TEXT = """**🤖 أوامر الأدمن**

**- رفع مشرف:** (بالرد) لترقية عضو إلى مشرف في المجموعة.
**- تنزيل مشرف:** (بالرد) لعزل مشرف من المجموعة.
**- ضع ترحيب:** لوضع رسالة ترحيب مخصصة.
**- حذف الترحيب:** لحذف رسالة الترحيب المخصصة.
**- ضع قوانين:** لوضع قوانين المجموعة.
**- حذف القوانين:** لحذف قوانين المجموعة.
**- تفعيل وتعطيل الأوامر:** للتحكم بالأوامر المسموحة في المجموعة.
"""

GROUP_ADMIN_COMMANDS_TEXT = """**🛡️ أوامر المدير (المشرف)**

**- حظر:** (بالرد) لحظر عضو من المجموعة.
**- الغاء الحظر:** (بالرد) لفك حظر عضو.
**- كتم:** (بالرد أو بالأمر) لكتم عضو.
**- الغاء الكتم:** (بالرد) لفك كتم عضو.
**- تحذير:** (بالرد) لتوجيه تحذير لعضو.
**- حذف التحذيرات:** (بالرد) لمسح تحذيرات عضو.
**- القوانين:** لعرض قوانين المجموعة.
**- تثبيت:** (بالرد) لتثبيت رسالة.
**- تاك للكل:** لعمل منشن لجميع أعضاء المجموعة.
"""

# --- معالج قائمة الإدارة ---

@client.on(events.CallbackQuery(pattern=b"^admin_hub:"))
async def admin_hub_handler(event):
    if not await check_activation(event.chat_id): return
    
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.answer("🚫 | هذا القسم مخصص للمشرفين فما فوق.", alert=True)

    data_parts = event.data.decode().split(':')
    action = data_parts[1] if len(data_parts) > 1 else "main"

    text = ""
    buttons = []

    if action == "main":
        text = "**⚙️ | قائمة الإدارة الرئيسية**\n\n**اختر القسم الذي تريد عرض أوامره:**"
        buttons = [
            [Button.inline("أوامر المالكين 👑", data="admin_hub:owner")],
            [Button.inline("أوامر المنشئين ⚜️", data="admin_hub:creator")],
            [Button.inline("أوامر الأدمنية 🤖", data="admin_hub:bot_admin")],
            [Button.inline("أوامر المدراء 🛡️", data="admin_hub:group_admin")],
            [Button.inline("إعدادات التفعيل والتعطيل 🔧", data="settings:main")],
            [Button.inline("إعدادات الحماية 🔒", data="protection_menu")],
            [Button.inline("🔙 عودة", data="back_to_main")]
        ]
    elif action == "owner":
        text = OWNER_COMMANDS_TEXT
        buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    elif action == "creator":
        text = CREATOR_COMMANDS_TEXT
        buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    elif action == "bot_admin":
        text = BOT_ADMIN_COMMANDS_TEXT
        buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    elif action == "group_admin":
        text = GROUP_ADMIN_COMMANDS_TEXT
        buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
        
    # التحقق من صلاحية المستخدم لعرض القائمة
    required_rank_map = {
        "owner": Ranks.OWNER,
        "creator": Ranks.CREATOR,
        "bot_admin": Ranks.BOT_ADMIN,
        "group_admin": Ranks.GROUP_ADMIN
    }
    
    required_rank = required_rank_map.get(action)
    if required_rank and user_rank < required_rank:
        return await event.answer(f"🚫 | هذه القائمة مخصصة لرتبة {action.replace('_', ' ').title()} فما فوق.", alert=True)

    await event.edit(text, buttons=buttons)
