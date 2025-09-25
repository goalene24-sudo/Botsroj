import asyncio
from telethon import events
from bot import client
# --- (تم التعديل) استيراد المكونات الجديدة ---
from .utils import (
    get_user_rank, Ranks, check_activation,
    PERCENT_COMMANDS, GAME_COMMANDS, ADMIN_COMMANDS
)
from sqlalchemy.future import select
from sqlalchemy import delete
from database import AsyncDBSession
from models import Alias

# --- (مُصحَّح) إضافة اختصار رفع مطور ثانوي ---
FIXED_ALIASES = {
    # الأوامر الأساسية
    "ا": "ايدي",
    "س": "سجلي",
    "رتبتي": "رتبتي",
    "ق": "القوانين",
    "الرابط": "الرابط",
    "تكك": "نداء",

    # أوامر الإدارة
    "اد": "رفع ادمن",
    "تاد": "تنزيل ادمن",
    "من": "رفع منشئ",
    "تمن": "تنزيل منشئ",
    "ر م": "رفع مميز",
    "ت م": "تنزيل مميز",
    "ر مط": "رفع مطور ثانوي", # تمت الإضافة
    "ط": "طرد",
    "ت": "تثبيت",
    "ضت": "ضع ترحيب",
    "حت": "حذف الترحيب",
    "رد": "اضف رد",
    "مر": "مسح رد",
    "رر": "الردود",
    "تف ص ا": "تشغيل صورة ايدي",
    "تع ص ا": "تعطيل صورة ايدي",

    # أوامر الحماية (قفل)
    "ق ص": "قفل الصور",
    "ق ف": "قفل الفيديو",
    "ق ر": "قفل الروابط",
    "ق ت": "قفل التوجيه",
    "ق م": "قفل الملصقات",
    "ق ك": "قفل الكلايش",
    "ق د": "قفل الدردشه",
    "ق ج": "قفل الجهات",

    # أوامر الحماية (فتح)
    "ف ص": "فتح الصور",
    "ف ف": "فتح الفيديو",
    "ف ر": "فتح الروابط",
    "ف ت": "فتح التوجيه",
    "ف م": "فتح الملصقات",
    "ف ك": "فتح الكلايش",
    "ف د": "فتح الدردشه",
    "ف ج": "فتح الجهات",
}

# --- قائمة شاملة بكل الأوامر المعروفة في البوت للتحقق منها ---
SERVICE_COMMANDS = [
    "اضف كلمة ممنوعة", "حذف كلمة ممنوعة", "الكلمات الممنوعة", "نداء", "@all", "طقس", 
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

    # --- تم التعديل هنا ---
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")

    original_command = None

    try:
        async with client.conversation(event.chat_id, timeout=180) as conv:
            await conv.send_message("""**تمام، لنقم بإضافة اختصار جديد.

**الخطوة 1 من 2:**
**أرسل الآن الأمر الأصلي الموجود في البوت (مثال: `ايدي`).**

**💡 ملاحظة: يمكنك كتابة `الغاء` في أي وقت للخروج.**
""")
            
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
**أرسل الآن الأمر الجديد (الاختصار) الذي تريده (مثال: `اا`).**

**💡 ملاحظة: يمكنك كتابة `الغاء` في أي وقت للخروج.**
""")

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
            
            async with AsyncDBSession() as session:
                result = await session.execute(
                    select(Alias).where(Alias.chat_id == event.chat_id, Alias.alias_name == alias_command)
                )
                existing_alias = result.scalar_one_or_none()

                if existing_alias or alias_command in FIXED_ALIASES:
                    await alias_command_msg.reply(f"**⚠️ عذراً، الاختصار `{alias_command}` مستخدم بالفعل.**")
                    return

                new_alias = Alias(chat_id=event.chat_id, alias_name=alias_command, command_name=original_command)
                session.add(new_alias)
                await session.commit()

            await alias_command_msg.reply(f"**✅ | تم الحفظ بنجاح!**\n\n**الآن عند إرسال `{alias_command}`، سيتم تنفيذ الأمر `{original_command}`.**")

    except asyncio.TimeoutError:
        await event.reply("**⏰ | انتهى الوقت. لقد استغرقت وقتاً طويلاً للرد.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ غير متوقع:**\n`{e}`")


@client.on(events.NewMessage(pattern=r"^حذف امر (.+)$"))
async def delete_alias_handler(event):
    if not await check_activation(event.chat_id): return
    # --- تم التعديل هنا ---
    user_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    if user_rank < Ranks.MOD:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")
    
    alias_to_delete = event.pattern_match.group(1).strip()
    
    if alias_to_delete in FIXED_ALIASES:
        return await event.reply(f"**⚠️ | لا يمكن حذف الاختصار الأساسي `{alias_to_delete}`.**")

    async with AsyncDBSession() as session:
        stmt = delete(Alias).where(Alias.chat_id == event.chat_id, Alias.alias_name == alias_to_delete)
        result = await session.execute(stmt)
        await session.commit()
        
        if result.rowcount > 0:
            await event.reply(f"**🗑️ | تم حذف الاختصار `{alias_to_delete}` بنجاح.**")
        else:
            await event.reply(f"**⚠️ | لم أجد الاختصار `{alias_to_delete}` في قائمة الأوامر المضافة.**")


@client.on(events.NewMessage(pattern="^الاوامر المضافة$"))
async def list_aliases_handler(event):
    if not await check_activation(event.chat_id): return
    
    async with AsyncDBSession() as session:
        result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
        user_aliases_rows = result.scalars().all()
        user_aliases = {alias.alias_name: alias.command_name for alias in user_aliases_rows}

    all_aliases = FIXED_ALIASES.copy()
    all_aliases.update(user_aliases)

    if not all_aliases:
        return await event.reply("**ℹ️ | لا توجد أي أوامر مضافة (اختصارات) في هذه المجموعة بعد.**")

    reply_text = "**📋 | قائمة الأوامر المضافة (الاختصارات):**\n\n"
    for alias, original in all_aliases.items():
        marker = " (أساسي)" if alias in FIXED_ALIASES and alias not in user_aliases else ""
        reply_text += f"**- `{alias}` ⇜ `{original}`{marker}**\n"
    
    await event.reply(reply_text)


@client.on(events.NewMessage(pattern="^ترتيب الاوامر$"))
async def sort_aliases_handler(event):
    if not await check_activation(event.chat_id): return
    
    async with AsyncDBSession() as session:
        result = await session.execute(select(Alias).where(Alias.chat_id == event.chat_id))
        user_aliases_rows = result.scalars().all()
        user_aliases = {alias.alias_name: alias.command_name for alias in user_aliases_rows}

    reply_text = "**ترتيب الاوامر**\n\n"
    reply_text += "**◇ : تم ترتيب الاوامر بالشكل التالي ~**\n\n"
    
    # عرض القائمة الثابتة بالترتيب
    sorted_fixed = sorted(FIXED_ALIASES.items())
    for alias, original in sorted_fixed:
        reply_text += f"**◇ : {original} - {alias}**\n"
    
    # عرض القائمة المخصصة إذا وجدت
    if user_aliases:
        reply_text += "\n**--- الأوامر المخصصة ---**\n"
        sorted_user = sorted(user_aliases.items())
        for alias, original in sorted_user:
            reply_text += f"**◇ : {original} - {alias}**\n"
    
    await event.reply(reply_text)
