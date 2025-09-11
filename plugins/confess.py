# plugins/confess.py
from telethon import events
from bot import client
import config

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from sqlalchemy import delete
from database import DBSession
from models import GlobalSetting # <-- يفترض وجود هذا النموذج

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, has_bot_permission

# --- دوال مساعدة لإدارة الإعدادات العامة في قاعدة البيانات ---
async def get_global_setting(key):
    """جلب قيمة إعداد عام من قاعدة البيانات."""
    async with DBSession() as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

async def set_global_setting(key, value):
    """حفظ أو تحديث قيمة إعداد عام في قاعدة البيانات."""
    async with DBSession() as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            new_setting = GlobalSetting(key=key, value=str(value))
            session.add(new_setting)
        await session.commit()

async def delete_global_setting(key):
    """حذف إعداد عام من قاعدة البيانات."""
    async with DBSession() as session:
        await session.execute(delete(GlobalSetting).where(GlobalSetting.key == key))
        await session.commit()


@client.on(events.NewMessage(pattern="^تفعيل الصراحة هنا$"))
async def set_confession_chat_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): 
        return await event.reply("بس المشرفين يگدرون يفعلون هاي الميزة.")
    
    chat_id = event.chat_id
    await set_global_setting("confession_target_chat", chat_id)
    await event.reply("✅ تمام، تم تفعيل الصراحة. أي اعتراف يوصلني بالخاص راح يتم نشره هنا بسرية تامة.")

@client.on(events.NewMessage(pattern="^تعطيل الصراحة هنا$"))
async def unset_confession_chat_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): 
        return await event.reply("بس المشرفين يگدرون يعطلون هاي الميزة.")
    
    chat_id = event.chat_id
    current_target_str = await get_global_setting("confession_target_chat")
    
    if current_target_str and int(current_target_str) == chat_id:
        await delete_global_setting("confession_target_chat")
        await event.reply("✅ خوش، تم تعطيل الصراحة. لن يتم نشر أي اعترافات جديدة هنا بعد الآن.")
    else:
        await event.reply("ميزة الصراحة هي أصلاً غير مفعلة في هذه المجموعة.")

@client.on(events.NewMessage(pattern=r"^ضع قناة سجل الصراحة (.+)"))
async def set_confession_log_handler(event):
    if event.is_private: return
    if event.sender_id not in config.SUDO_USERS:
        return await event.reply("فقط المطور الرئيسي للبوت يستطيع تحديد قناة السجل.")
    
    channel_input = event.pattern_match.group(1)
    try:
        channel = await client.get_entity(channel_input)
        await set_global_setting("confession_log_channel", channel.id)
        await client.send_message(channel.id, "✅ سيتم استخدام هذه القناة لسجل الصراحة السري (للمشرفين فقط).")
        await event.reply("✅ تم تحديد قناة السجل بنجاح.")
    except Exception as e:
        await event.reply(f"ما گدرت أوصل للقناة. تأكد من الآيدي/المعرف وأن البوت مشرف بيها.\n`{e}`")

@client.on(events.NewMessage(pattern=r"^(?:/)?(?:صراحة|اعتراف)\s+([\s\S]+)", func=lambda e: e.is_private))
async def handle_confession_dm_handler(event):
    target_chat_str = await get_global_setting("confession_target_chat")
    if not target_chat_str:
        return await event.reply("عذراً، ميزة الصراحة معطلة حالياً أو لم يتم تفعيلها في أي مجموعة بعد.")

    target_chat = int(target_chat_str)
    confession_text = event.pattern_match.group(1).strip()
    sender = event.sender
    
    try:
        await client.send_message(target_chat, f"💬 **صراحة جديدة وردت للبوت:**\n\n{confession_text}")
        await event.reply("✅ تم إرسال صراحتك للمجموعة بنجاح وبدون إظهار اسمك.")
    except Exception as e:
        await event.reply(f"ما گدرت أرسل صراحتك، صارت مشكلة:\n`{e}`")
        return

    log_channel_str = await get_global_setting("confession_log_channel")
    if log_channel_str:
        log_channel = int(log_channel_str)
        try:
            log_message = (
                f"**سجل صراحة جديد** 🤫\n\n"
                f"**من:** [{sender.first_name}](tg://user?id={sender.id})\n"
                f"**المعرف:** @{sender.username or 'لا يوجد'}\n"
                f"**الآيدي:** `{sender.id}`\n\n"
                f"**الرسالة:**\n{confession_text}"
            )
            await client.send_message(log_channel, log_message)
        except Exception as e:
            if config.SUDO_USERS:
                await client.send_message(config.SUDO_USERS[0], f"فشل تسجيل رسالة صراحة في قناة السجل!\n`{e}`")
