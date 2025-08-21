# plugins/replies.py
import asyncio
from telethon import events
from bot import client
from .utils import check_activation, has_bot_permission, db, save_db
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
            trigger = trigger_msg.text
            
            if trigger in DEFAULT_REPLIES:
                await conv.send_message("**⚠️ هذا الرد موجود مسبقاً في الردود الثابتة للبوت. تم إلغاء العملية.**")
                return

            await conv.send_message("**عاشت ايدك. هسه دزلي الرد مالتها.**")
            reply_msg = await conv.get_response()
            reply_text = reply_msg.text
            chat_id_str = str(event.chat_id)
            if chat_id_str not in db: db[chat_id_str] = {}
            if "custom_replies" not in db[chat_id_str]: db[chat_id_str]["custom_replies"] = {}
            db[chat_id_str]["custom_replies"][trigger] = reply_text; save_db(db)
            
            await conv.send_message(f"**✅ انحفظ الرد بنجاح للمجموعة.**\n**الكلمة:** `{trigger}`\n**الرد:** `{reply_text}`")
    except asyncio.TimeoutError:
        await client.send_message(event.sender_id, "**تأخرت هواي ومادزيت شي. تم إلغاء العملية.**")

@client.on(events.NewMessage(pattern=r"^حذف رد (.+)"))
async def delete_reply_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية يگدرون يمسحون ردود.**")
    trigger_to_delete = event.pattern_match.group(1)
    chat_id_str = str(event.chat_id)
    if chat_id_str in db and "custom_replies" in db[chat_id_str] and trigger_to_delete in db[chat_id_str]["custom_replies"]:
        del db[chat_id_str]["custom_replies"][trigger_to_delete]; save_db(db)
        await event.reply(f"**🗑️ خوش، مسحت الرد مال `{trigger_to_delete}`.**")
    else:
        await event.reply(f"**ما لگيت هيچ رد `{trigger_to_delete}` أصلاً.**")

@client.on(events.NewMessage(pattern="^الردود$"))
async def list_replies_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية يگدرون يشوفون الردود.**")
    
    chat_id_str = str(event.chat_id)
    sender_id = event.sender_id

    if chat_id_str in db and "custom_replies" in db[chat_id_str] and db[chat_id_str]["custom_replies"]:
        replies = db[chat_id_str]["custom_replies"]
        response = f"**💬 الردود المخصصة في مجموعة `{event.chat.title}`:**\n\n"
        for trigger, reply in replies.items():
            response += f"- **الكلمة:** `{trigger}`\n- **الرد:** `{reply}`\n\n"
        
        try:
            await client.send_message(sender_id, response)
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
    chat_id_str = str(event.chat_id)
    if chat_id_str not in db: db[chat_id_str] = {}
    db[chat_id_str]["dev_reply"] = reply_text; save_db(db)
    await event.reply(f"**✅ تمام، حفظت الرد الخاص بالمطور: `{reply_text}`**")

@client.on(events.NewMessage(pattern=r"^ضع رد المناداة(?: (.*))?$"))
async def set_call_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    reply_text = event.pattern_match.group(1)
    if not reply_text: return await event.reply("**الأمر يحتاج رد. الاستخدام الصحيح:\n`ضع رد المناداة [الرد الذي تريده]`**")
    reply_text = reply_text.strip()
    chat_id_str = str(event.chat_id)
    if chat_id_str not in db: db[chat_id_str] = {}
    db[chat_id_str]["call_reply"] = reply_text; save_db(db)
    await event.reply(f"**✅ تمام، حفظت رد المناداة للعامة: `{reply_text}`**")

@client.on(events.NewMessage(pattern="^مسح رد المطور$"))
async def delete_dev_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    chat_id_str = str(event.chat_id)
    if chat_id_str in db and "dev_reply" in db[chat_id_str]:
        del db[chat_id_str]["dev_reply"]
        save_db(db)
        await event.reply("**🗑️ تم مسح الرد الخاص بالمطور. سأستخدم الرد الافتراضي الآن.**")
    else:
        await event.reply("**لا يوجد رد خاص بالمطور محفوظ أصلاً لمسحه.**")

@client.on(events.NewMessage(pattern="^مسح رد المناداة$"))
async def delete_call_reply(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): return await event.reply("**بس المشرفين والأدمنية.**")
    chat_id_str = str(event.chat_id)
    if chat_id_str in db and "call_reply" in db[chat_id_str]:
        del db[chat_id_str]["call_reply"]
        save_db(db)
        await event.reply("**🗑️ تم مسح رد المناداة العام. سأستخدم الرد الافتراضي الآن.**")
    else:
        await event.reply("**لا يوجد رد مناداة عام محفوظ أصلاً لمسحه.**")
