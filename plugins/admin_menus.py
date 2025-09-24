# plugins/admin_menus.py
from telethon import events, Button
from bot import client
# --- استيراد الرتب المحدثة والدوال ---
from .utils import check_activation, Ranks, get_user_rank, build_protection_menu

# --- نصوص قوائم الأوامر الجديدة ---

OWNER_COMMANDS_TEXT = """**👑 أوامر المالك**
**- رفع منشئ:** (بالرد) لترقية عضو إلى رتبة منشئ.
**- تنزيل منشئ:** (بالرد) لعزل عضو من رتبة المنشئ.
**- المنشئين:** لعرض قائمة المنشئين في المجموعة.
**- مسح المنشئين:** لحذف جميع المنشئين في المجموعة.
**- رفع مالك:** (بالرد) يمكن للمالك رفع نفسه مالك بالبوت اذا كان عضو.
**- رفع مطور ثانوي:** (بالرد) لترقية مطور ثانوي.
**- تنزيل مطور ثانوي:** (بالرد) لعزل مطور ثانوي.
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
**- رفع مميز:** (بالرد) لترقية عضو إلى رتبة مميز.
**- تنزيل مميز:** (بالرد) لعزل عضو من المميزين.
**- المميزين:** لعرض قائمة المميزين.
**- ضع ترحيب:** لوضع رسالة ترحيب مخصصة.
**- حذف الترحيب:** لحذف رسالة الترحيب المخصصة.
**- ضع قوانين:** لوضع قوانين المجموعة.
**- حذف القوانين:** لحذف قوانين المجموعة.
**- تشغيل صورة ايدي:** لعرض الصورة في أمر ايدي.
**- تعطيل صورة ايدي:** لإخفاء الصورة في أمر ايدي.
**- تفعيل وتعطيل الأوامر:** للتحكم بالأوامر المسموحة في المجموعة.
"""

GROUP_ADMIN_COMMANDS_TEXT = """**🛡️ أوامر المدير (المشرف)**
**- طرد:** (بالرد) لطرد عضو من المجموعة.
**- حظر:** (بالرد) لحظر عضو من المجموعة.
**- الغاء الحظر:** (بالرد) لفك حظر عضو.
**- كتم:** (بالرد أو بالأمر) لكتم عضو.
**- الغاء الكتم:** (بالرد) لفك كتم عضو.
**- تحذير:** (بالرد) لتوجيه تحذير لعضو.
**- حذف التحذيرات:** (بالرد) لمسح تحذيرات عضو.
**- القوانين:** لعرض قوانين المجموعة.
**- تثبيت:** (بالرد) لتثبيت رسالة.
**- نداء:** لعمل منشن لجميع أعضاء المجموعة.
**- منشن [نص]:** (بالرد) لعمل منشن مخصص باسم من اختيارك.
**- تحليل او التحليل:** لمعرفه احصائيات المجموعة بشكل دقيق في اي ساعه اكثر نشاط و اكثر كلمه مكرره الخ.
**- قفل/فتح الكل:** للمشرفين فقط يقوم بقفل المجموعه او فتحها.
**- `تفعيل/ايقاف وضع الحماية `: يقوم بالتحقق من الاعضاء الجدد الذين ينضمون للمجموعه عن طريق زر اثبت انك انسان.**

**--- أوامر الاختصارات ---**
**- اضف امر:** لإنشاء اختصار لأمر موجود.
**- حذف امر:** (بعده اسم الاختصار) لحذف اختصار.
**- الاوامر المضافة:** لعرض كل الاختصارات.
"""

CLEANING_COMMANDS_TEXT = """**🧹 | أوامر المسح والتنظيف**
تحتوي هذه القائمة على شرح لجميع أوامر المسح المتاحة. استخدمها بحذر.

**• لمسح عدد معين من الرسائل (كل الأنواع):**
`مسح` + عدد
مثال: `مسح 50`

**• لمسح الرسائل بالرد (من رسالة إلى أخرى):**
- قم بالرد على الرسالة التي تريد بدء الحذف منها واكتب `مسح`

**• لمسح أنواع معينة من الرسائل:**
`مسح الصور`
`مسح الميديا` (صور، فيديو، ملصقات، متحركات)
`مسح الكلايش` (الرسائل الطويلة)
`مسح الروابط`
`مسح التوجيه`

**💡 ملاحظة هامة:**
- يمكنك إضافة عدد بعد الأوامر أعلاه لحذف عدد معين (مثال: `مسح الصور 10`).
- إذا لم تقم بإضافة عدد، سيتم حذف كل الرسائل من ذلك النوع المحفوظة في ذاكرة البوت (بحد أقصى 100).

**• لضبط حجم الكلايش:**
`ضع حجم الكلايش` + عدد
مثال: `ضع حجم الكلايش 150`
"""

# --- معالج قائمة الإدارة ---

@client.on(events.CallbackQuery(pattern=b"^admin_hub:"))
async def admin_hub_handler(event):
    if not await check_activation(event.chat_id): return
    
    # --- تم التعديل هنا: إضافة event.client ---
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD:
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
            [Button.inline("أوامر المسح 🧹", data="admin_hub:cleaning_help")],
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
    elif action == "cleaning_help":
        text = CLEANING_COMMANDS_TEXT
        buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
        
    required_rank_map = {
        "owner": Ranks.OWNER,
        "creator": Ranks.CREATOR,
        "bot_admin": Ranks.ADMIN,
        "group_admin": Ranks.MOD
    }
    
    required_rank = required_rank_map.get(action)
    if required_rank and user_rank < required_rank:
        return await event.answer(f"🚫 | هذه القائمة غير متاحة لرتبتك.", alert=True)

    await event.edit(text, buttons=buttons)
