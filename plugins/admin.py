# plugins/admin.py
import asyncio
import re
from datetime import timedelta
from telethon import events
from bot import client
import config
from .utils import check_activation, is_group_owner, has_bot_permission, db, save_db, get_user_rank

@client.on(events.NewMessage(pattern="^ضع قوانين$"))
async def set_rules_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**بس المشرفين والأدمنية يگدرون يغيرون القوانين.**")
    try:
        async with client.conversation(event.sender_id, timeout=300) as conv:
            await conv.send_message("**تمام، دزلي هسه قوانين المجموعة الجديدة نصاً كاملاً...**")
            response = await conv.get_response(from_users=event.sender_id)
            rules_text = response.text
            chat_id_str = str(event.chat_id)
            if chat_id_str not in db: db[chat_id_str] = {}
            db[chat_id_str]["rules"] = rules_text
            save_db(db)
            await conv.send_message("**✅ عاشت ايدك، حفظت القوانين الجديدة للمجموعة.**")
    except asyncio.TimeoutError:
        await event.reply("**تأخرت هواي ومادزيت شي. من تريد تعدل صيحني مرة لخ.**")

@client.on(events.NewMessage(pattern="^القوانين$"))
async def get_rules_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    chat_id_str = str(event.chat_id)
    rules = db.get(chat_id_str, {}).get("rules")
    if rules:
        await event.reply(f"**📜 قوانين المجموعة:**\n\n**{rules}**")
    else:
        await event.reply("**لم يتم وضع قوانين لهذه المجموعة بعد.**")

@client.on(events.NewMessage(pattern="^حذف القوانين$"))
async def delete_rules_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**بس المشرفين والأدمنية يگدرون يحذفون القوانين.**")
    chat_id_str = str(event.chat_id)
    if db.get(chat_id_str, {}).get("rules"):
        del db[chat_id_str]["rules"]
        save_db(db)
        await event.reply("**🗑️ خوش، مسحت القوانين. صارت المجموعة بلا قوانين حالياً.**")
    else:
        await event.reply("**هي أصلاً ماكو قوانين حتى أحذفها.**")

@client.on(events.NewMessage(pattern=r"^تثبيت (\d+)\s*([ديس])$"))
async def temporary_pin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event): 
        return await event.reply("**هاي الشغلة بس للمشرفين والأدمنية.**")
    reply = await event.get_reply_message()
    if not reply:
        return await event.reply("**لازم ترد على رسالة حتى أثبتها.**")
    try:
        me = await client.get_me()
        bot_perms = await client.get_permissions(event.chat_id, me.id)
        if not bot_perms.pin_messages:
            return await event.reply("**ما عندي صلاحية أثبت رسايل يابه. ارفعني مشرف وانطيني الصلاحية.**")
    except Exception as e:
        return await event.reply(f"**ما گدرت أتأكد من صلاحياتي: {e}**")
    try:
        time_value = int(event.pattern_match.group(1))
        time_unit = event.pattern_match.group(2).lower()
        duration_seconds = 0
        if time_unit == 'د': duration_seconds = time_value * 60
        elif time_unit == 'س': duration_seconds = time_value * 3600
        elif time_unit == 'ي': duration_seconds = time_value * 86400
        if duration_seconds <= 0:
            return await event.reply("**المدة لازم تكون أكثر من صفر.**")
        duration_text = f"{time_value} { {'د': 'دقايق', 'س': 'ساعات', 'ي': 'أيام'}[time_unit] }"
        await client.pin_message(event.chat_id, reply.id, notify=False)
        await event.reply(f"**✅ تمام، ثبتت الرسالة لمدة {duration_text}.**")
        await asyncio.sleep(duration_seconds)
        await client.unpin_message(event.chat_id, reply.id)
    except Exception as e:
        await event.reply(f"**ما گدرت أنفذ الأمر، صارت مشكلة: {e}**")

@client.on(events.NewMessage(pattern="^(ضع ترحيب|حذف الترحيب)$"))
async def welcome_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**بس المشرفين والأدمنية يگدرون يعدلون الترحيب.**")
    action = event.raw_text
    chat_id_str = str(event.chat_id)
    if action == "حذف الترحيب":
        if db.get(chat_id_str, {}).get("welcome_message"):
            del db[chat_id_str]["welcome_message"]
            save_db(db)
            await event.reply("**🗑️ خوش، مسحت الترحيب المخصص.**")
        else:
            await event.reply("**هو أصلاً ماكو ترحيب مخصص حتى أحذفه.**")
    else: # ضع ترحيب
        try:
            async with client.conversation(event.sender_id, timeout=180) as conv:
                await conv.send_message("**تمام، دزلي رسالة الترحيب الجديدة.\n\n💡 ملاحظة:\n`{user}` - لمنشن العضو الجديد.\n`{group}` - لاسم المجموعة.**")
                response = await conv.get_response(from_users=event.sender_id)
                if chat_id_str not in db: db[chat_id_str] = {}
                db[chat_id_str]["welcome_message"] = response.text
                save_db(db)
                await event.client.send_message(event.chat_id, "**✅ عاشت ايدك، حفظت رسالة الترحيب المخصصة.**")
        except asyncio.TimeoutError:
            await event.reply("**تأخرت هواي ومادزيت شي. حاول مرة لخ.**")

@client.on(events.NewMessage(pattern=r"^(رفع مشرف|تنزيل مشرف)$"))
async def promote_demote_handler(event):
    # ... الكود هنا يبقى كما هو ...
    pass

@client.on(events.NewMessage(pattern="^(رفع ادمن|تنزيل ادمن|الادمنيه|مسح كل الادمنيه)$"))
async def bot_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action, chat_id_str = event.raw_text, str(event.chat_id)
    is_owner_or_sudo = await is_group_owner(event.chat_id, event.sender_id) or event.sender_id in config.SUDO_USERS
    
    if action == "مسح كل الادمنيه":
        if not is_owner_or_sudo:
            return await event.reply("**فقط المالك والمطور يستطيعون استخدام هذا الأمر.**")
        if db.get(chat_id_str, {}).get("bot_admins"):
            db[chat_id_str]["bot_admins"] = []
            save_db(db)
            await event.reply("**✅ تم مسح قائمة الأدمنية لهذه المجموعة بنجاح. يمكنك الآن إضافة الأدمنية الصحيحين.**")
        else:
            await event.reply("**القائمة فارغة أصلاً.**")
        return

    if action in ["رفع ادمن", "تنزيل ادمن"]:
        if not is_owner_or_sudo:
            return await event.reply("**فقط المالك والمطور يستطيعون رفع وتنزيل أدمنية في البوت.**")
        reply = await event.get_reply_message()
        if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
        user_to_manage = await reply.get_sender()
        if chat_id_str not in db: db[chat_id_str] = {}
        if "bot_admins" not in db[chat_id_str]: db[chat_id_str]["bot_admins"] = []
        if action == "رفع ادمن":
            if user_to_manage.id in db[chat_id_str]["bot_admins"]: return await event.reply("**هذا الشخص هو أصلاً أدمن بالبوت.**")
            db[chat_id_str]["bot_admins"].append(user_to_manage.id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) أدمن في البوت.**")
        else: # تنزيل ادمن
            if user_to_manage.id not in db[chat_id_str]["bot_admins"]: return await event.reply("**هذا الشخص هو مو أدمن بالبوت أصلاً.**")
            db[chat_id_str]["bot_admins"].remove(user_to_manage.id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من أدمنية البوت.**")
        save_db(db)
    
    elif action == "الادمنيه":
        if not await has_bot_permission(event): return
        bot_admins_ids = db.get(chat_id_str, {}).get("bot_admins", [])
        if not bot_admins_ids: return await event.reply("**ماكو أي أدمن بالبوت حالياً بهاي المجموعة.**")
        admin_list_text = "**⚜️ قائمة الأدمنية في البوت:**\n\n"
        for admin_id in bot_admins_ids:
            try:
                user = await client.get_entity(admin_id)
                admin_list_text += f"- [{user.first_name}](tg://user?id={user.id})\n"
            except Exception:
                admin_list_text += f"- `{admin_id}` (يمكن غادر المجموعة)\n"
        await event.reply(admin_list_text)

@client.on(events.NewMessage(pattern=r"^(تاك للكل|@all)(?: ([\s\S]*))?$"))
async def tag_all_handler(event):
    # ... الكود هنا يبقى كما هو ...
    pass
