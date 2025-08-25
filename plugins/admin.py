# plugins/admin.py
import asyncio
import re
from datetime import timedelta
from telethon import events
from bot import client
import config
from .utils import check_activation, has_bot_permission, db, save_db, get_user_rank, Ranks

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
    
    actor_rank = await get_user_rank(event.sender_id, event)

    if action in ["رفع ادمن", "تنزيل ادمن", "مسح كل الادمنيه"]:
        if actor_rank < Ranks.CREATOR: # الصلاحية الآن للمنشئ فما فوق
            return await event.reply("**فقط المنشئين والمالك والمطور يستطيعون استخدام هذا الأمر.**")
        
        if action == "مسح كل الادمنيه":
            if db.get(chat_id_str, {}).get("bot_admins"):
                db[chat_id_str]["bot_admins"] = []
                save_db(db)
                await event.reply("**✅ تم مسح قائمة الأدمنية لهذه المجموعة بنجاح.**")
            else:
                await event.reply("**القائمة فارغة أصلاً.**")
            return

        reply = await event.get_reply_message()
        if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
        user_to_manage = await reply.get_sender()
        user_to_manage_id = user_to_manage.id
        
        target_rank = await get_user_rank(user_to_manage_id, event)
        if target_rank >= actor_rank:
            return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

        if chat_id_str not in db: db[chat_id_str] = {}
        if "bot_admins" not in db[chat_id_str]: db[chat_id_str]["bot_admins"] = []

        if action == "رفع ادمن":
            if user_to_manage_id in db[chat_id_str]["bot_admins"]: return await event.reply("**هذا الشخص هو أصلاً أدمن بالبوت.**")
            db[chat_id_str]["bot_admins"].append(user_to_manage_id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) أدمن في البوت.**")
        else: # تنزيل ادمن
            if user_to_manage_id not in db[chat_id_str]["bot_admins"]: return await event.reply("**هذا الشخص هو مو أدمن بالبوت أصلاً.**")
            db[chat_id_str]["bot_admins"].remove(user_to_manage_id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) من أدمنية البوت.**")
        save_db(db)
    
    elif action == "الادمنيه":
        if await get_user_rank(event.sender_id, event) < Ranks.GROUP_ADMIN: return
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
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**هذا الأمر للمشرفين فقط.**")
    
    msg = await event.reply("**📣 جاري تحضير المنشن...**")
    
    text = event.pattern_match.group(2) or ""
    users_text = f"**{text}**\n\n"
    
    try:
        participants = await client.get_participants(event.chat_id)
        for user in participants:
            if not user.bot:
                mention = f"• [{user.first_name}](tg://user?id={user.id})\n"
                if len(users_text + mention) > 4000:
                    await client.send_message(event.chat_id, users_text)
                    users_text = ""
                    await asyncio.sleep(1) 
                users_text += mention
        
        if users_text.strip():
            await client.send_message(event.chat_id, users_text)
        
        await msg.delete()
        
    except Exception as e:
        await msg.edit(f"**حدث خطأ أثناء عمل المنشن:**\n`{e}`**")

# --- (جديد) أوامر إدارة المنشئين ---
@client.on(events.NewMessage(pattern="^(رفع منشئ|تنزيل منشئ|المنشئين|مسح المنشئين)$"))
async def creator_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    action = event.raw_text
    chat_id_str = str(event.chat_id)
    
    actor_rank = await get_user_rank(event.sender_id, event)
    
    if action in ["رفع منشئ", "تنزيل منشئ", "مسح المنشئين"]:
        if actor_rank < Ranks.OWNER:
            return await event.reply("**فقط مالك المجموعة والمطور يستطيعون استخدام هذا الأمر.**")
        
        if action == "مسح المنشئين":
            if db.get(chat_id_str, {}).get("creators"):
                db[chat_id_str]["creators"] = []
                save_db(db)
                await event.reply("**✅ تم مسح قائمة المنشئين لهذه المجموعة بنجاح.**")
            else:
                await event.reply("**القائمة فارغة أصلاً.**")
            return

        reply = await event.get_reply_message()
        if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
        
        user_to_manage = await reply.get_sender()
        user_to_manage_id = user_to_manage.id
        
        target_rank = await get_user_rank(user_to_manage_id, event)
        if target_rank >= actor_rank:
            return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")
        
        if chat_id_str not in db: db[chat_id_str] = {}
        if "creators" not in db[chat_id_str]: db[chat_id_str]["creators"] = []
        
        if action == "رفع منشئ":
            if user_to_manage_id in db[chat_id_str]["creators"]:
                return await event.reply("**هذا الشخص هو أصلاً منشئ.**")
            db[chat_id_str]["creators"].append(user_to_manage_id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) إلى منشئ في البوت.**")
        else: # تنزيل منشئ
            if user_to_manage_id not in db[chat_id_str]["creators"]:
                return await event.reply("**هذا الشخص هو ليس منشئاً أصلاً.**")
            db[chat_id_str]["creators"].remove(user_to_manage_id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) من المنشئين.**")
        save_db(db)

    elif action == "المنشئين":
        if actor_rank < Ranks.GROUP_ADMIN: return
        
        creator_ids = db.get(chat_id_str, {}).get("creators", [])
        if not creator_ids:
            return await event.reply("**لا يوجد أي منشئين في البوت حالياً بهذه المجموعة.**")
            
        list_text = "**⚜️ قائمة المنشئين في البوت:**\n\n"
        for user_id in creator_ids:
            try:
                user = await client.get_entity(user_id)
                list_text += f"- [{user.first_name}](tg://user?id={user.id})\n"
            except Exception:
                list_text += f"- `{user_id}` (ربما غادر المجموعة)\n"
        await event.reply(list_text)
