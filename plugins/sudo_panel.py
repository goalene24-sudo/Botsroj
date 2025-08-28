# plugins/sudo_panel.py

import asyncio
import os
import sys
from datetime import datetime
from telethon import events, Button
from bot import client, StartTime
import config
from .utils import db, get_uptime_string

# --- الدالة الرئيسية لبناء أزرار لوحة التحكم ---
def build_sudo_panel():
    buttons = [
        [Button.inline("📊 الإحصائيات العامة", data="sudo_panel:stats")],
        [Button.inline("📢 قسم الإذاعة", data="sudo_panel:broadcast")],
        [Button.inline("🔄 إعادة التشغيل", data="sudo_panel:restart"), Button.inline("🛑 إيقاف التشغيل", data="sudo_panel:shutdown")],
        [Button.inline("📁 تحميل قاعدة البيانات", data="sudo_panel:get_db")],
    ]
    return buttons

# --- نص الرسالة الرئيسية للوحة التحكم ---
SUDO_PANEL_TEXT = "**⚙️ | لوحة تحكم المطور**\n\n**أهلاً بك يا مطوري. اختر أحد الأقسام للتحكم بالبوت:**"

# --- معالج الأمر الرئيسي لفتح اللوحة ---
@client.on(events.NewMessage(pattern="^/لوحه$"))
async def open_sudo_panel(event):
    # التأكد من أن الأمر في الخاص ومن المطور فقط
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return
    
    await event.reply(SUDO_PANEL_TEXT, buttons=build_sudo_panel())


# --- معالج ضغطات الأزرار في لوحة التحكم ---
@client.on(events.CallbackQuery(pattern=b"^sudo_panel:"))
async def sudo_panel_callback(event):
    # التأكد من أن المستخدم هو المطور
    if event.sender_id not in config.SUDO_USERS:
        return await event.answer("🚫 | هذه اللوحة مخصصة للمطور فقط.", alert=True)

    action = event.data.decode().split(':')[1]

    if action == "main":
        await event.edit(SUDO_PANEL_TEXT, buttons=build_sudo_panel())

    elif action == "restart":
        await event.edit("**🔄 | جاري إعادة تشغيل البوت...**")
        # هذا الأمر يقوم بإعادة تشغيل البوت من نقطة البداية
        os.execl(sys.executable, sys.executable, "-m", "main")

    elif action == "shutdown":
        await event.edit("**🛑 | جاري إيقاف تشغيل البوت... إلى اللقاء.**")
        # هذا الأمر يوقف البوت بشكل كامل
        await client.disconnect()

    elif action == "stats":
        # حساب الإحصائيات
        uptime = get_uptime_string(StartTime)
        group_count = len(db)
        
        # حساب عدد المستخدمين الفريدين
        unique_users = set()
        for chat_data in db.values():
            if "users" in chat_data:
                unique_users.update(chat_data["users"].keys())
        user_count = len(unique_users)

        stats_text = f"""**📊 | الإحصائيات العامة للبوت**

**- مدة التشغيل (Uptime):**
  `{uptime}`

**- عدد المجموعات المفعلة:**
  `{group_count}` **مجموعة**

**- عدد المستخدمين المسجلين:**
  `{user_count}` **مستخدم**
"""
        await event.edit(stats_text, buttons=[Button.inline("🔙 رجوع", data="sudo_panel:main")])
    
    elif action == "broadcast":
        try:
            async with client.conversation(event.sender_id, timeout=300) as conv:
                await conv.send_message("**📢 | أرسل الآن رسالة الإذاعة التي تريد إرسالها لجميع المجموعات...**\n\n**(للإلغاء، أرسل `الغاء`)**")
                
                response = await conv.get_response()
                if response.text.strip() == "الغاء":
                    return await conv.send_message("**☑️ | تم إلغاء الإذاعة.**")
                
                broadcast_message = response.message
                await conv.send_message("**⏳ | تم استلام الرسالة. سأبدأ الآن ببثها إلى جميع المجموعات. قد يستغرق هذا بعض الوقت...**")
                
                successful_sends = 0
                failed_sends = 0
                
                all_chats = list(db.keys())
                for chat_id_str in all_chats:
                    try:
                        chat_id = int(chat_id_str)
                        await client.send_message(chat_id, broadcast_message)
                        successful_sends += 1
                        await asyncio.sleep(0.5) # فاصل زمني لتجنب الحظر
                    except Exception as e:
                        print(f"Broadcast failed for chat {chat_id_str}: {e}")
                        failed_sends += 1
                
                await conv.send_message(f"""**📡 | اكتملت عملية الإذاعة!**

**- ✅ نجح الإرسال إلى:** `{successful_sends}` **مجموعة**
**- ❌ فشل الإرسال إلى:** `{failed_sends}` **مجموعة**
""")
        except asyncio.TimeoutError:
            await event.reply("**⏰ | انتهى الوقت.**")
        
        await event.answer()

    elif action == "get_db":
        await event.answer("📁 | جاري تحضير ملف قاعدة البيانات...")
        try:
            await client.send_file(
                event.chat_id,
                "database.json",
                caption="**🗄️ | النسخة الاحتياطية من قاعدة البيانات `database.json`**"
            )
        except Exception as e:
            await event.reply(f"**حدث خطأ أثناء إرسال الملف:**\n`{e}`")