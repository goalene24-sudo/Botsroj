# plugins/admin.py
import asyncio
import re
from datetime import timedelta
from telethon import events
from bot import client
import config
# --- (مُعَدَّل) استيراد الدوال والرتب المحدثة ---
from .utils import check_activation, has_bot_permission, db, save_db, get_user_rank, Ranks, build_protection_menu

# --- قاموس أنواع الأقفال للترجمة من العربية إلى مفاتيح قاعدة البيانات ---
LOCK_TYPES_MAP = {
    # الوسائط الأساسية
    "الصور": "photo",
    "الفيديو": "video",
    "المتحركه": "gif",
    "الملصقات": "sticker",
    "الروابط": "url",
    "المعرف": "username",
    "التوجيه": "forward",
    "الملفات": "document",
    "الاغاني": "audio",
    "الصوت": "voice",
    "السيلفي": "video_note",
    
    # أنواع الرسائل
    "الكلايش": "long_text",
    "الدردشه": "text",
    "الانلاين": "inline",
    "البوتات": "bot",
    
    # أنواع المحتوى
    "الجهات": "contact",
    "الموقع": "location",
    "الفشار": "game",
    
    # اللغات (تحتاج لتفعيل في events.py)
    "الانكليزيه": "english",
    
    # الإجراءات (تحتاج لتفعيل في events.py)
    "التعديل": "edit",
}

# --- أمر الطرد (مُعَدَّل) ---
@client.on(events.NewMessage(pattern="^طرد$"))
async def kick_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    if not await has_bot_permission(event):
        return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")

    reply = await event.get_reply_message()
    if not reply:
        return await event.reply("**⚠️ | يجب استخدام هذا الأمر بالرد على رسالة شخص لطرده.**")

    user_to_kick = await reply.get_sender()
    actor = await event.get_sender()
    
    # --- (جديد) التحقق إذا كان المستهدف هو البوت نفسه ---
    me = await client.get_me()
    if user_to_kick.id == me.id:
        return await event.reply("**تريدني اطرد نفسي شدتحس بله😒**")

    if user_to_kick.id == actor.id:
        return await event.reply("**لا يمكنك طرد نفسك!**")

    try:
        bot_perms = await client.get_permissions(event.chat_id, me.id)
        if not bot_perms.ban_users:
            return await event.reply("**⚠️ | ليس لدي صلاحية طرد الأعضاء في هذه المجموعة.**")
    except Exception:
        return await event.reply("**⚠️ | لا أستطيع التحقق من صلاحياتي، يرجى التأكد من أنني مشرف.**")

    actor_rank = await get_user_rank(actor.id, event.chat_id)
    target_rank = await get_user_rank(user_to_kick.id, event.chat_id)

    if target_rank >= actor_rank:
        return await event.reply("**❌ | لا يمكنك طرد شخص يمتلك رتبة مساوية لك أو أعلى.**")

    try:
        await client.kick_participant(event.chat_id, user_to_kick.id)
        await event.reply(f"**✅ | تم طرد العضو [{user_to_kick.first_name}](tg://user?id={user_to_kick.id}) من المجموعة بنجاح.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ أثناء محاولة طرد العضو:**\n`{str(e)}`")


@client.on(events.NewMessage(pattern=r"^(قفل|فتح) (.+)$"))
async def lock_unlock_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")
    
    action = event.pattern_match.group(1)
    target = event.pattern_match.group(2).strip()
    
    lock_key = LOCK_TYPES_MAP.get(target)
    
    if not lock_key:
        return await event.reply(f"**⚠️ | الأمر `{target}` غير معروف.**\n**قائمة الأوامر المتاحة:**\n`" + "`, `".join(LOCK_TYPES_MAP.keys()) + "`")

    chat_id_str = str(event.chat_id)
    db_key = f"lock_{lock_key}"
    
    if chat_id_str not in db: db[chat_id_str] = {}

    current_state_is_locked = db.get(chat_id_str, {}).get(db_key, False)
    change_made = False

    if action == "قفل":
        if current_state_is_locked:
            return await event.reply(f"**🔒 | {target} مقفلة بالفعل، لا تقلق عزيزي.**")
        else:
            db[chat_id_str][db_key] = True
            await event.reply(f"**✅ | تم قفل {target} بنجاح.**")
            change_made = True
    elif action == "فتح":
        if not current_state_is_locked:
            return await event.reply(f"**🔓 | {target} مفتوحة بالفعل.**")
        else:
            db[chat_id_str][db_key] = False
            await event.reply(f"**✅ | تم فتح {target} بنجاح.**")
            change_made = True
    
    if change_made:
        save_db(db)
        protection_menu_msg_id = db.get(chat_id_str, {}).get("protection_menu_msg_id")
        if protection_menu_msg_id:
            try:
                menu_text = "**🛡️ قائمة الحماية التفاعلية** 🛡️\n**دوس على أي دگمة حتى تغير حالتها.**"
                new_buttons = await build_protection_menu(event.chat_id)
                await client.edit_message(event.chat_id, protection_menu_msg_id, menu_text, buttons=new_buttons)
            except Exception as e:
                print(f"Failed to update protection menu: {e}")
                if "protection_menu_msg_id" in db.get(chat_id_str, {}):
                    del db[chat_id_str]["protection_menu_msg_id"]
                    save_db(db)

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

@client.on(events.NewMessage(pattern="^(رفع ادمن|تنزيل ادمن|الادمنيه|مسح الادمنيه)$"))
async def bot_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text.replace(" كل", "")
    chat_id_str = str(event.chat_id)
    
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action in ["رفع ادمن", "تنزيل ادمن", "مسح الادمنيه"]:
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**فقط المنشئ والمطور يستطيعون استخدام هذا الأمر.**")
        
        if action == "مسح الادمنيه":
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
        if user_to_manage.bot:
            return await event.reply("**لا يمكنك ترقية البوتات إلى رتبة أدمن.**")
        
        user_to_manage_id = user_to_manage.id
        
        target_rank = await get_user_rank(user_to_manage_id, event.chat_id)
        if target_rank >= actor_rank:
            return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

        if chat_id_str not in db: db[chat_id_str] = {}
        if "bot_admins" not in db[chat_id_str]: db[chat_id_str]["bot_admins"] = []

        if action == "رفع ادمن":
            if user_to_manage_id in db[chat_id_str]["bot_admins"]: return await event.reply("**هذا الشخص هو أصلاً أدمن بالبوت.**")
            db[chat_id_str]["bot_admins"].append(user_to_manage_id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) أدمن في البوت.**")
        else: 
            if user_to_manage_id not in db[chat_id_str]["bot_admins"]: return await event.reply("**هذا الشخص هو مو أدمن بالبوت أصلاً.**")
            db[chat_id_str]["bot_admins"].remove(user_to_manage_id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) من أدمنية البوت.**")
        save_db(db)
    
    elif action == "الادمنيه":
        if await get_user_rank(event.sender_id, event.chat_id) < Ranks.MOD: return
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

@client.on(events.NewMessage(pattern=r"^(نداء|@all)(?: ([\s\S]*))?$"))
async def tag_all_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**هذا الأمر للمشرفين فقط.**")
    
    msg = await event.reply("**📣 جاري تحضير النداء...**")
    
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
        await msg.edit(f"**حدث خطأ أثناء عمل النداء:**\n`{e}`**")

@client.on(events.NewMessage(pattern="^(رفع منشئ|تنزيل منشئ|المنشئين|مسح المنشئين|رفع مالك)$"))
async def creator_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    action = event.raw_text
    chat_id_str = str(event.chat_id)
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    
    if action == "رفع مالك":
        if actor_rank < Ranks.OWNER:
            return await event.reply("**فقط المالك الفعلي للمجموعة يستطيع استخدام هذا الأمر.**")

        reply = await event.get_reply_message()
        if not reply:
            return await event.reply(f"**✅ أهلاً بك يا مالك المجموعة!**\n**البوت يتعرف عليك بصفتك المالك الأعلى لهذه المجموعة.**")
        
        action = "رفع منشئ"

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
        if user_to_manage.bot:
            return await event.reply("**لا يمكنك ترقية البوتات إلى رتبة منشئ.**")
            
        user_to_manage_id = user_to_manage.id
        
        target_rank = await get_user_rank(user_to_manage_id, event.chat_id)
        if target_rank >= actor_rank:
            return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")
        
        if chat_id_str not in db: db[chat_id_str] = {}
        if "creators" not in db[chat_id_str]: db[chat_id_str]["creators"] = []
        
        if action == "رفع منشئ":
            if user_to_manage_id in db[chat_id_str]["creators"]:
                return await event.reply("**هذا الشخص هو أصلاً منشئ.**")
            db[chat_id_str]["creators"].append(user_to_manage_id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) إلى منشئ في البوت.**")
        else:
            if user_to_manage_id not in db[chat_id_str]["creators"]:
                return await event.reply("**هذا الشخص هو ليس منشئاً أصلاً.**")
            db[chat_id_str]["creators"].remove(user_to_manage_id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) من المنشئين.**")
        save_db(db)

    elif action == "المنشئين":
        if actor_rank < Ranks.MOD: return
        
        creator_ids = db.get(chat_id_str, {}).get("creators", [])
        if not creator_ids:
            return await event.reply("**لا يوجد أي منشئين في البوت حالياً بهذه المجموعة.**")
            
        list_text = "**⚜️ قائمة المنشئين في البوت:**\n\n"
        for user_id in creator_ids:
            try:
                user = await client.get_entity(user_id)
                list_text += f"- [{user.first_name}](tg://user?id={user_id})\n"
            except Exception:
                list_text += f"- `{user_id}` (ربما غادر المجموعة)\n"
        await event.reply(list_text)

# --- أوامر المطور الثانوي ---
@client.on(events.NewMessage(pattern="^(رفع مطور ثانوي|تنزيل مطور ثانوي|المطورين الثانويين|مسح المطورين الثانويين)$"))
async def secondary_dev_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text
    chat_id_str = str(event.chat_id)
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action in ["رفع مطور ثانوي", "تنزيل مطور ثانوي", "مسح المطورين الثانويين"]:
        if actor_rank not in [Ranks.MAIN_DEV, Ranks.OWNER]:
            return await event.reply("**فقط المطور الرئيسي ومالك المجموعة يستطيعون استخدام هذا الأمر.**")
        
        if action == "مسح المطورين الثانويين":
            if db.get(chat_id_str, {}).get("secondary_devs"):
                db[chat_id_str]["secondary_devs"] = []
                save_db(db)
                await event.reply("**✅ تم مسح قائمة المطورين الثانويين لهذه المجموعة بنجاح.**")
            else:
                await event.reply("**القائمة فارغة أصلاً.**")
            return

        reply = await event.get_reply_message()
        if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
        user_to_manage = await reply.get_sender()
        if user_to_manage.bot:
            return await event.reply("**لا يمكنك ترقية البوتات لهذه الرتبة.**")
        
        user_to_manage_id = user_to_manage.id
        
        target_rank = await get_user_rank(user_to_manage_id, event.chat_id)
        if target_rank >= actor_rank:
            return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

        if chat_id_str not in db: db[chat_id_str] = {}
        if "secondary_devs" not in db[chat_id_str]: db[chat_id_str]["secondary_devs"] = []

        if action == "رفع مطور ثانوي":
            if user_to_manage_id in db[chat_id_str]["secondary_devs"]:
                return await event.reply("**هذا الشخص هو أصلاً مطور ثانوي.**")
            db[chat_id_str]["secondary_devs"].append(user_to_manage_id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) إلى مطور ثانوي.**")
        else:
            if user_to_manage_id not in db[chat_id_str]["secondary_devs"]:
                return await event.reply("**هذا الشخص ليس مطور ثانوي أصلاً.**")
            db[chat_id_str]["secondary_devs"].remove(user_to_manage_id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) من المطورين الثانويين.**")
        save_db(db)

    elif action == "المطورين الثانويين":
        if actor_rank < Ranks.ADMIN: return
        
        dev_ids = db.get(chat_id_str, {}).get("secondary_devs", [])
        if not dev_ids:
            return await event.reply("**لا يوجد أي مطورين ثانويين في المجموعة.**")
            
        list_text = "**⚜️ قائمة المطورين الثانويين:**\n\n"
        for user_id in dev_ids:
            try:
                user = await client.get_entity(user_id)
                list_text += f"- [{user.first_name}](tg://user?id={user_id})\n"
            except Exception:
                list_text += f"- `{user_id}` (ربما غادر المجموعة)\n"
        await event.reply(list_text)

# --- أوامر العضو المميز ---
@client.on(events.NewMessage(pattern="^(رفع مميز|تنزيل مميز|المميزين|مسح المميزين)$"))
async def vip_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text
    chat_id_str = str(event.chat_id)
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action in ["رفع مميز", "تنزيل مميز", "مسح المميزين"]:
        if actor_rank < Ranks.ADMIN:
            return await event.reply("**هذا الأمر للادمنية فما فوق.**")
        
        if action == "مسح المميزين":
            if db.get(chat_id_str, {}).get("vips"):
                db[chat_id_str]["vips"] = []
                save_db(db)
                await event.reply("**✅ تم مسح قائمة الأعضاء المميزين لهذه المجموعة بنجاح.**")
            else:
                await event.reply("**القائمة فارغة أصلاً.**")
            return

        reply = await event.get_reply_message()
        if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
        user_to_manage = await reply.get_sender()
        if user_to_manage.bot:
            return await event.reply("**لا يمكنك ترقية البوتات لهذه الرتبة.**")
        
        user_to_manage_id = user_to_manage.id
        
        target_rank = await get_user_rank(user_to_manage_id, event.chat_id)
        if target_rank >= actor_rank:
            return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

        if chat_id_str not in db: db[chat_id_str] = {}
        if "vips" not in db[chat_id_str]: db[chat_id_str]["vips"] = []

        if action == "رفع مميز":
            if user_to_manage_id in db[chat_id_str]["vips"]:
                return await event.reply("**هذا الشخص هو أصلاً عضو مميز.**")
            db[chat_id_str]["vips"].append(user_to_manage_id)
            await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) إلى عضو مميز.**")
        else:
            if user_to_manage_id not in db[chat_id_str]["vips"]:
                return await event.reply("**هذا الشخص ليس عضو مميز أصلاً.**")
            db[chat_id_str]["vips"].remove(user_to_manage_id)
            await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage_id}) من المميزين.**")
        save_db(db)

    elif action == "المميزين":
        if actor_rank < Ranks.MOD: return
        
        vip_ids = db.get(chat_id_str, {}).get("vips", [])
        if not vip_ids:
            return await event.reply("**لا يوجد أي أعضاء مميزين في المجموعة.**")
            
        list_text = "**⚜️ قائمة الأعضاء المميزين:**\n\n"
        for user_id in vip_ids:
            try:
                user = await client.get_entity(user_id)
                list_text += f"- [{user.first_name}](tg://user?id={user_id})\n"
            except Exception:
                list_text += f"- `{user_id}` (ربما غادر المجموعة)\n"
        await event.reply(list_text)

@client.on(events.NewMessage(pattern=r"^ضع حجم الكلايش (\d+)$"))
async def set_long_text_size(event):
    if not await check_activation(event.chat_id): 
        return

    rank = await get_user_rank(event.sender_id, event.chat_id)
    if rank < Ranks.MOD:
        return await event.reply("**هذا الأمر متاح للمشرفين فما فوق.**")

    try:
        size = int(event.pattern_match.group(1))
    except (ValueError, IndexError):
        return await event.reply("⚠️ يرجى تحديد رقم صحيح.")

    if not (50 <= size <= 2000):
        return await event.reply("⚠️ حجم الكلايش يجب أن يكون بين 50 و 2000 حرف.")

    chat_id_str = str(event.chat_id)
    if chat_id_str not in db: 
        db[chat_id_str] = {}

    db[chat_id_str]["long_text_size"] = size
    save_db(db)
    
    await event.reply(f"✅ **تم تحديث الإعدادات بنجاح.**\nسيتم اعتبار أي رسالة أطول من **{size}** حرف 'كليشة'.")
