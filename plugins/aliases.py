# plugins/aliases.py

import asyncio
from telethon import events
from bot import client
from .utils import (
    db, save_db, get_user_rank, Ranks, check_activation,
    PERCENT_COMMANDS, GAME_COMMANDS, ADMIN_COMMANDS
)

# --- (جديد) قاموس الاختصارات الأساسية والثابتة ---
FIXED_ALIASES = {
    "ا": "ايدي",
    "م": "رفع مميز",
    "اد": "رفع ادمن",
    "مد": "رفع مدير",
    "من": "رفع منشئ",
    "مط": "رفع مطور",
    "تك": "تنزيل الكل بالرد",
    "تغ": "تغيير الايدي",
    "تنز": "تنزيل جميع الرتب",
    "ر": "الرابط",
    "رر": "الردود",
    "ت": "تثبيت",
    "ك": "كشف",
    "تكك": "نداء",
    "رف": "رفع القيود",
    "الغ": "الغاء حظر",
    "رد": "اضف رد",
    "مر": "مسح رد"
}

# --- قائمة شاملة بكل الأوامر المعروفة في البوت للتحقق منها ---
SERVICE_COMMANDS = [
    "اضف كلمة ممنوعة", "حذف كلمة ممنوعة", "الكلمات الممنوعة", "تاك للكل", "@all", "طقس", 
    "معلومات المجموعة", "احصائيات", "ضع رد المطور", "ضع رد المناداة", "مسح رد المطور", 
    "مسح رد المناداة", "احجي", "حظي", "فككها", "صندوق الحظ", "ضع ترحيب", "حذف الترحيب", 
    "تثبيت", "تفعيل الصراحة هنا", "تعطيل الصراحة هنا", "ضع قناة سجل الصراحة", "سبحة", 
    "اسماء الله الحسنى", "سيرة النبي", "ضع قوانين", "القوانين", "حذف القوانين", "نشاطك", "عمري",
    "ضع حجم الكلايش"
]
OTHER_COMMANDS = [
    "الاوامر", "الردود", "ايدي", "id", "اضف رد", "حذف رد", "تفعيل", "ايقاف", "تحذير", 
    "حذف التحذيرات", "اذكار الصباح", "اذكار المساء", "راتب", "ضع نبذة", "المتجر", "شراء", 
    "طلاق", "ممتلكاتي", "نقاطي", "صديقي المفضل", "حذف صديقي المفضل", "ضع ميلادي", "حللني", 
    "حلل", "لو خيروك", "تحدي نرد", "ميمز", "سمايلات", "سمايل", "اضف امر", "حذف امر", "الاوامر المضافة",
    "مسح", "سجلي", "اهداء", "رتبتي", "نكتة", "حزورة", "كت", "الترتيب", "زواج", "اقتباس",
    "همس", "صفعة", "بوسة", "عناق", "غمزة", "قتل", "رزالة", "تزوجني", "اخطبني", "من هو"
]
ALL_BOT_COMMANDS = PERCENT_COMMANDS + GAME_COMMANDS + ADMIN_COMMANDS + SERVICE_COMMANDS + OTHER_COMMANDS


@client.on(events.NewMessage(pattern="^اضف امر$"))
async def add_alias_handler(event):
    if not await check_activation(event.chat_id): return

    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")

    chat_id_str = str(event.chat_id)
    original_command = None

    try:
        async with client.conversation(event.chat_id, timeout=180) as conv:
            await conv.send_message("""**تمام، لنقم بإضافة اختصار جديد.

**الخطوة 1 من 2:**
**أرسل الآن الأمر الأصلي الموجود في البوت (مثال: `ايدي`).**

**💡 ملاحظة: يمكنك كتابة `الغاء` في أي وقت للخروج.**
**""")
            
            while True:
                response = await conv.get_response()
                if response.sender_id != event.sender_id: continue
                if response.text.strip() in ["الغاء", "إلغاء"]:
                    await response.reply("**✅ | تم إلغاء عملية إضافة الأمر.**")
                    return

                command_to_check = response.text.strip().split(" ")[0]
                if command_to_check in ALL_BOT_COMMANDS:
                    original_command = response.text.strip()
                    break
                else:
                    await response.reply("**⚠️ | عذراً، هذا الأمر (`%s`) غير موجود في قائمة الأوامر الأساسية. يرجى إرسال أمر صحيح.**" % command_to_check)
            
            await response.reply(f"""**حسناً، الأمر الأصلي هو: `{original_command}`

**الخطوة 2 من 2:**
**أرسل الآن الأمر الجديد (الاختصار) الذي تريده (مثال: `ا`).**

**💡 ملاحظة: يمكنك كتابة `الغاء` في أي وقت للخروج.**
**""")

            alias_command_msg = None
            while True:
                response = await conv.get_response()
                if response.sender_id == event.sender_id:
                    if response.text.strip() in ["الغاء", "إلغاء"]:
                        await response.reply("**✅ | تم إلغاء عملية إضافة الأمر.**")
                        return
                    alias_command_msg = response
                    break

            alias_command = alias_command_msg.text.strip()
            
            if chat_id_str not in db: db[chat_id_str] = {}
            if "command_aliases" not in db[chat_id_str]:
                db[chat_id_str]["command_aliases"] = {}

            # --- (مُعدل) التحقق من القائمة الثابتة والمخصصة ---
            user_aliases = db[chat_id_str]["command_aliases"]
            if alias_command in user_aliases or alias_command in FIXED_ALIASES:
                await alias_command_msg.reply(f"**⚠️ عذراً، الاختصار `{alias_command}` مستخدم بالفعل.**")
                return

            user_aliases[alias_command] = original_command
            save_db(db)

            await alias_command_msg.reply(f"**✅ | تم الحفظ بنجاح!**\n\n**الآن عند إرسال `{alias_command}`، سيتم تنفيذ الأمر `{original_command}`.**")

    except asyncio.TimeoutError:
        await event.reply("**⏰ | انتهى الوقت. لقد استغرقت وقتاً طويلاً للرد.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ غير متوقع:**\n`{e}`")


@client.on(events.NewMessage(pattern=r"^حذف امر (.+)$"))
async def delete_alias_handler(event):
    if not await check_activation(event.chat_id): return
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")
    
    chat_id_str = str(event.chat_id)
    alias_to_delete = event.pattern_match.group(1).strip()
    
    # لا يمكن حذف الاختصارات الثابتة
    if alias_to_delete in FIXED_ALIASES:
        return await event.reply(f"**⚠️ | لا يمكن حذف الاختصار الأساسي `{alias_to_delete}`.**")

    aliases = db.get(chat_id_str, {}).get("command_aliases", {})
    if alias_to_delete in aliases:
        del db[chat_id_str]["command_aliases"][alias_to_delete]
        save_db(db)
        await event.reply(f"**🗑️ | تم حذف الاختصار `{alias_to_delete}` بنجاح.**")
    else:
        await event.reply(f"**⚠️ | لم أجد الاختصار `{alias_to_delete}` في قائمة الأوامر المضافة.**")


@client.on(events.NewMessage(pattern="^الاوامر المضافة$"))
async def list_aliases_handler(event):
    if not await check_activation(event.chat_id): return
    chat_id_str = str(event.chat_id)
    
    # --- (مُعدل) دمج القائمتين ---
    user_aliases = db.get(chat_id_str, {}).get("command_aliases", {})
    all_aliases = FIXED_ALIASES.copy()
    all_aliases.update(user_aliases)

    if not all_aliases:
        return await event.reply("**ℹ️ | لا توجد أي أوامر مضافة (اختصارات) في هذه المجموعة بعد.**")

    reply_text = "**📋 | قائمة الأوامر المضافة (الاختصارات):**\n\n"
    for alias, original in all_aliases.items():
        # تمييز الأوامر الثابتة (اختياري)
        marker = " (أساسي)" if alias in FIXED_ALIASES and alias not in user_aliases else ""
        reply_text += f"**- `{alias}` ⇜ `{original}`{marker}**\n"
    
    await event.reply(reply_text)


@client.on(events.NewMessage(pattern="^ترتيب الاوامر$"))
async def sort_aliases_handler(event):
    if not await check_activation(event.chat_id): return
    chat_id_str = str(event.chat_id)

    # --- (مُعدل) دمج القائمتين ---
    user_aliases = db.get(chat_id_str, {}).get("command_aliases", {})
    all_aliases = FIXED_ALIASES.copy()
    all_aliases.update(user_aliases)

    if not all_aliases:
        return await event.reply("**ℹ️ | لم يتم إضافة أي أوامر مخصصة لهذه المجموعة بعد.**")

    reply_text = "**ترتيب الاوامر**\n\n"
    reply_text += "**◇ : تم ترتيب الاوامر بالشكل التالي ~**\n\n"
    
    # العرض يبدأ بالقائمة الثابتة ثم المخصصة
    sorted_fixed = sorted(FIXED_ALIASES.items())
    sorted_user = sorted(user_aliases.items())

    for alias, original in sorted_fixed:
        reply_text += f"**◇ : {original} - {alias}**\n"
    
    if user_aliases:
        reply_text += "\n**--- الأوامر المخصصة ---**\n"
        for alias, original in sorted_user:
            reply_text += f"**◇ : {original} - {alias}**\n"
    
    await event.reply(reply_text)
