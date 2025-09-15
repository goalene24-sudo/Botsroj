import asyncio
from telethon import events
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, has_bot_permission
from .utils import get_or_create_chat
from .default_replies import DEFAULT_REPLIES

@client.on(events.NewMessage(pattern="^اضف رد$"))
async def add_reply_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية يگدرون يضيفون ردود.**")
    
    try:
        await client.send_message(event.sender_id, "**أهلاً بك! لنقم بإضافة رد جديد من مجموعة...**")
    except Exception:
        return await event.reply("**ما أگدر أراسلك على الخاص. 😕\nلطفاً، تأكد أنك لم تقم بحظري وابدأ محادثة معي أولاً ثم حاول مرة أخرى.**")

    await event.reply("**✅ تمام، شوف الخاص مالتك حتى نكمل...**")

    try:
        async with client.conversation(event.sender_id, timeout=120) as conv:
            await conv.send_message("**يلا، دزلي الكلمة اللي تريدني أرد عليها.**")
            trigger_msg = await conv.get_response()
            trigger = trigger_msg.text.strip()
            
            if not trigger:
                return await conv.send_message("**تم إلغاء العملية لأن الكلمة فارغة.**")

            if trigger in DEFAULT_REPLIES:
                await conv.send_message("**⚠️ هذا الرد موجود مسبقاً في الردود الثابتة للبوت. تم إلغاء العملية.**")
                return

            await conv.send_message("**عاشت ايدك. هسه دزلي الرد مالتها.**")
            reply_msg = await conv.get_response()
            reply_text = reply_msg.text.strip()
            
            if not reply_text:
                return await conv.send_message("**تم إلغاء العملية لأن الرد فارغ.**")

            async with AsyncDBSession() as session:
                chat = await get_or_create_chat(session, event.chat_id)
                custom_replies = chat.custom_replies or {}
                custom_replies[trigger] = reply_text
                chat.custom_replies = custom_replies
                flag_modified(chat, "custom_replies")
                await session.commit()
            
            await conv.send_message(f"**✅ انحفظ الرد بنجاح للمجموعة.**\n**الكلمة:** `{trigger}`\n**الرد:** `{reply_text}`")
    except asyncio.TimeoutError:
        await client.send_message(event.sender_id, "**تأخرت هواي ومادزيت شي. تم إلغاء العملية.**")


@client.on(events.NewMessage(pattern=r"^حذف رد (.+)"))
async def delete_reply_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية يگدرون يمسحون ردود.**")
    
    trigger_to_delete = event.pattern_match.group(1).strip()
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        custom_replies = chat.custom_replies or {}

        if trigger_to_delete in custom_replies:
            del custom_replies[trigger_to_delete]
            chat.custom_replies = custom_replies
            flag_modified(chat, "custom_replies")
            await session.commit()
            await event.reply(f"**🗑️ خوش، مسحت الرد مال `{trigger_to_delete}`.**")
        else:
            await event.reply(f"**ما لگيت هيچ رد `{trigger_to_delete}` أصلاً.**")


@client.on(events.NewMessage(pattern="^الردود$"))
async def list_replies_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية يگدرون يشوفون الردود.**")
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        replies = chat.custom_replies or {}

    if replies:
        response = f"**💬 الردود المخصصة في مجموعة `{event.chat.title}`:**\n\n"
        for trigger, reply in replies.items():
            response += f"- **الكلمة:** `{trigger}`\n- **الرد:** `{reply}`\n\n"
        
        try:
            await client.send_message(event.sender_id, response)
            confirm_msg = await event.reply("**✅ تمام، دزيتلك قائمة الردود على الخاص.**")
            await asyncio.sleep(5)
            await confirm_msg.delete()
        except Exception:
            await event.reply("**ما أگدر أراسلك على الخاص. لطفاً، تأكد أنك لم تقم بحظري وابدأ محادثة معي أولاً.**")
            
    else:
        await event.reply("**ماكو ولا رد مخصص بالمجموعة حالياً.**")


@client.on(events.NewMessage(pattern=r"^ضع رد المطور(?: (.*))?$"))
async def set_dev_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    
    reply_text = event.pattern_match.group(1)
    if not reply_text: return await event.reply("**الأمر يحتاج رد. الاستخدام الصحيح:\n`ضع رد المطور [الرد الذي تريده]`**")
    
    reply_text = reply_text.strip()
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        settings["dev_reply"] = reply_text
        chat.settings = settings
        flag_modified(chat, "settings")
        await session.commit()

    await event.reply(f"**✅ تمام، حفظت الرد الخاص بالمطور: `{reply_text}`**")


@client.on(events.NewMessage(pattern=r"^ضع رد المناداة(?: (.*))?$"))
async def set_call_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    
    reply_text = event.pattern_match.group(1)
    if not reply_text: return await event.reply("**الأمر يحتاج رد. الاستخدام الصحيح:\n`ضع رد المناداة [الرد الذي تريده]`**")
    
    reply_text = reply_text.strip()
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        settings["call_reply"] = reply_text
        chat.settings = settings
        flag_modified(chat, "settings")
        await session.commit()

    await event.reply(f"**✅ تمام، حفظت رد المناداة للعامة: `{reply_text}`**")


@client.on(events.NewMessage(pattern="^مسح رد المطور$"))
async def delete_dev_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        if "dev_reply" in settings:
            del settings["dev_reply"]
            chat.settings = settings
            flag_modified(chat, "settings")
            await session.commit()
            await event.reply("**🗑️ تم مسح الرد الخاص بالمطور. سأستخدم الرد الافتراضي الآن.**")
        else:
            await event.reply("**لا يوجد رد خاص بالمطور محفوظ أصلاً لمسحه.**")


@client.on(events.NewMessage(pattern="^مسح رد المناداة$"))
async def delete_call_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        if "call_reply" in settings:
            del settings["call_reply"]
            chat.settings = settings
            flag_modified(chat, "settings")
            await session.commit()
            await event.reply("**🗑️ تم مسح رد المناداة العام. سأستخدم الرد الافتراضي الآن.**")
        else:
            await event.reply("**لا يوجد رد مناداة عام محفوظ أصلاً لمسحه.**")
