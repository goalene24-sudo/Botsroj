#admin.py
import asyncio
from telethon import events
from bot import client
import json

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from sqlalchemy import delete
# (تم التعديل) استيراد الجلسة الغير متزامنة الجديدة
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, SecondaryDev, Vip

# --- استيراد الدوال والرتب المحدثة ---
from .utils import check_activation, has_bot_permission, get_user_rank, Ranks, build_protection_menu

# --- دوال مساعدة لإدارة إعدادات المجموعة ---

async def get_or_create_chat(session, chat_id):
    """الحصول على مجموعة من قاعدة البيانات أو إنشائها إذا لم تكن موجودة."""
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(id=chat_id, settings={}, lock_settings={})
        session.add(chat)
        await session.commit()
    return chat

async def get_chat_setting(chat_id, key, default=None):
    """جلب قيمة إعداد معين من حقل JSON في جدول المجموعات."""
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        # تأكد من أن settings ليس None قبل الوصول إليه
        if chat.settings is None:
            chat.settings = {}
        return chat.settings.get(key, default)

async def set_chat_setting(chat_id, key, value):
    """حفظ أو تحديث قيمة إعداد معين في حقل JSON."""
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        # تأكد من أن settings ليس None
        if chat.settings is None:
            chat.settings = {}
        
        # قم بتحديث القيمة
        new_settings = chat.settings.copy()
        new_settings[key] = value
        chat.settings = new_settings
        
        await session.commit()

async def del_chat_setting(chat_id, key):
    """حذف إعداد معين من حقل JSON."""
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        if chat.settings and key in chat.settings:
            new_settings = chat.settings.copy()
            del new_settings[key]
            chat.settings = new_settings
            await session.commit()


# --- قاموس أنواع الأقفال للترجمة ---
LOCK_TYPES_MAP = {
    # الوسائط الأساسية
    "الصور": "photo", "الفيديو": "video", "المتحركه": "gif", "الملصقات": "sticker",
    "الروابط": "url", "المعرف": "username", "التوجيه": "forward", "الملفات": "document",
    "الاغاني": "audio", "الصوت": "voice", "السيلفي": "video_note",
    # أنواع الرسائل
    "الكلايش": "long_text", "الدردشه": "text", "الانلاين": "inline", "البوتات": "bot",
    # أنواع المحتوى
    "الجهات": "contact", "الموقع": "location", "الفشار": "game",
    # اللغات والإجراءات
    "الانكليزيه": "english", "التعديل": "edit",
}

# --- أمر الطرد ---
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
        return await event.reply(f"**⚠️ | الأمر `{target}` غير معروف.**")

    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        if chat.lock_settings is None:
            chat.lock_settings = {}
        
        new_lock_settings = chat.lock_settings.copy()
        current_state_is_locked = new_lock_settings.get(lock_key, False)

        if action == "قفل":
            if current_state_is_locked:
                return await event.reply(f"**🔒 | {target} مقفلة بالفعل، لا تقلق عزيزي.**")
            new_lock_settings[lock_key] = True
            await event.reply(f"**✅ | تم قفل {target} بنجاح.**")
        else: # فتح
            if not current_state_is_locked:
                return await event.reply(f"**🔓 | {target} مفتوحة بالفعل.**")
            new_lock_settings[lock_key] = False
            await event.reply(f"**✅ | تم فتح {target} بنجاح.**")
        
        chat.lock_settings = new_lock_settings
        await session.commit()


@client.on(events.NewMessage(pattern="^ضع قوانين$"))
async def set_rules_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**بس المشرفين والأدمنية يگدرون يغيرون القوانين.**")
    try:
        async with client.conversation(event.sender_id, timeout=300) as conv:
            await conv.send_message("**تمام، دزلي هسه قوانين المجموعة الجديدة نصاً كاملاً...**")
            response = await conv.get_response(from_users=event.sender_id)
            await set_chat_setting(event.chat_id, "rules", response.text)
            await conv.send_message("**✅ عاشت ايدك، حفظت القوانين الجديدة للمجموعة.**")
    except asyncio.TimeoutError:
        await event.reply("**تأخرت هواي ومادزيت شي. من تريد تعدل صيحني مرة لخ.**")


@client.on(events.NewMessage(pattern="^القوانين$"))
async def get_rules_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    rules = await get_chat_setting(event.chat_id, "rules")
    if rules:
        await event.reply(f"**📜 قوانين المجموعة:**\n\n**{rules}**")
    else:
        await event.reply("**لم يتم وضع قوانين لهذه المجموعة بعد.**")


@client.on(events.NewMessage(pattern="^حذف القوانين$"))
async def delete_rules_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**بس المشرفين والأدمنية يگدرون يحذفون القوانين.**")
    
    if await get_chat_setting(event.chat_id, "rules"):
        await del_chat_setting(event.chat_id, "rules")
        await event.reply("**🗑️ خوش، مسحت القوانين. صارت المجموعة بلا قوانين حالياً.**")
    else:
        await event.reply("**هي أصلاً ماكو قوانين حتى أحذفها.**")


@client.on(events.NewMessage(pattern="^(ضع ترحيب|حذف الترحيب)$"))
async def welcome_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**بس المشرفين والأدمنية يگدرون يعدلون الترحيب.**")
    
    action = event.raw_text
    if action == "حذف الترحيب":
        if await get_chat_setting(event.chat_id, "welcome_message"):
            await del_chat_setting(event.chat_id, "welcome_message")
            await event.reply("**🗑️ خوش، مسحت الترحيب المخصص.**")
        else:
            await event.reply("**هو أصلاً ماكو ترحيب مخصص حتى أحذفه.**")
    else:
        try:
            async with client.conversation(event.sender_id, timeout=180) as conv:
                await conv.send_message("**تمام، دزلي رسالة الترحيب الجديدة.\n\n💡 ملاحظة:\n`{user}` - لمنشن العضو الجديد.\n`{group}` - لاسم المجموعة.**")
                response = await conv.get_response(from_users=event.sender_id)
                await set_chat_setting(event.chat_id, "welcome_message", response.text)
                await event.client.send_message(event.chat_id, "**✅ عاشت ايدك، حفظت رسالة الترحيب المخصصة.**")
        except asyncio.TimeoutError:
            await event.reply("**تأخرت هواي ومادزيت شي. حاول مرة لخ.**")


@client.on(events.NewMessage(pattern="^(تشغيل|تعطيل) صورة ايدي$"))
async def toggle_id_photo_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await has_bot_permission(event):
        return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")
    
    action = event.pattern_match.group(1)
    if action == "تشغيل":
        await set_chat_setting(event.chat_id, "id_photo_enabled", True)
        await event.reply("**✅ | تم تشغيل عرض الصورة في أمر ايدي.**")
    else:
        await set_chat_setting(event.chat_id, "id_photo_enabled", False)
        await event.reply("**☑️ | تم تعطيل عرض الصورة في أمر ايدي.**")


@client.on(events.NewMessage(pattern=r"^(رفع مشرف|تنزيل مشرف)$"))
async def promote_demote_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.ADMIN:
        return await event.reply("**🚫 | هذا الأمر للادمنية فما فوق.**")

    reply = await event.get_reply_message()
    if not reply:
        return await event.reply("**⚠️ | يجب استخدام هذا الأمر بالرد على رسالة شخص.**")

    user_to_manage = await reply.get_sender()
    if user_to_manage.bot:
        return await event.reply("**لا يمكنك رفع أو تنزيل بوت كمشرف.**")
    if user_to_manage.id == event.sender_id:
        return await event.reply("**لا يمكنك تغيير رتبة نفسك.**")

    try:
        me = await client.get_me()
        bot_perms = await client.get_permissions(event.chat_id, me.id)
        if not bot_perms.add_admins:
            return await event.reply("**⚠️ | ليس لدي صلاحية إضافة مشرفين جدد في هذه المجموعة.**")
    except Exception:
        return await event.reply("**⚠️ | لا أستطيع التحقق من صلاحياتي، يرجى التأكد من أنني مشرف.**")

    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank:
        return await event.reply("**❌ | لا يمكنك إدارة شخص يمتلك رتبة مساوية لك أو أعلى.**")

    action = event.raw_text
    try:
        if action == "رفع مشرف":
            await client.edit_admin(event.chat_id, user_to_manage, change_info=True, delete_messages=True, ban_users=True, invite_users=True, pin_messages=True)
            await event.reply(f"**✅ | تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى مشرف.**")
        else:
            await client.edit_admin(event.chat_id, user_to_manage, is_admin=False)
            await event.reply(f"**☑️ | تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من الإشراف.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ:**\n`{str(e)}`")


# --- (مُحَدَّث) أوامر الأدمن ---
@client.on(events.NewMessage(pattern="^(رفع ادمن|تنزيل ادمن|الادمنيه|مسح الادمنيه)$"))
async def bot_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text.replace(" كل", "")
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action in ["رفع ادمن", "تنزيل ادمن", "مسح الادمنيه"]:
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**فقط المنشئ والمطور يستطيعون استخدام هذا الأمر.**")
        
        async with AsyncDBSession() as session:
            if action == "مسح الادمنيه":
                await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == event.chat_id))
                await session.commit()
                return await event.reply("**✅ تم مسح قائمة الأدمنية لهذه المجموعة بنجاح.**")

            reply = await event.get_reply_message()
            if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
            user_to_manage = await reply.get_sender()
            if user_to_manage.bot: return await event.reply("**لا يمكنك ترقية البوتات.**")
            
            target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
            if target_rank >= actor_rank:
                return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

            result = await session.execute(select(BotAdmin).where(BotAdmin.chat_id == event.chat_id, BotAdmin.user_id == user_to_manage.id))
            is_admin = result.scalar_one_or_none()

            if action == "رفع ادمن":
                if is_admin: return await event.reply("**هذا الشخص هو أصلاً أدمن بالبوت.**")
                session.add(BotAdmin(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) أدمن في البوت.**")
            else:
                if not is_admin: return await event.reply("**هذا الشخص هو مو أدمن بالبوت أصلاً.**")
                await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == event.chat_id, BotAdmin.user_id == user_to_manage.id))
                await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من أدمنية البوت.**")
            await session.commit()
    
    elif action == "الادمنيه":
        if actor_rank < Ranks.MOD: return
        async with AsyncDBSession() as session:
            result = await session.execute(select(BotAdmin.user_id).where(BotAdmin.chat_id == event.chat_id))
            bot_admins_ids = result.scalars().all()

        if not bot_admins_ids: return await event.reply("**ماكو أي أدمن بالبوت حالياً بهاي المجموعة.**")
        admin_list_text = "**⚜️ قائمة الأدمنية في البوت:**\n\n"
        for admin_id in bot_admins_ids:
            try:
                user = await client.get_entity(admin_id)
                admin_list_text += f"- [{user.first_name}](tg://user?id={user.id})\n"
            except Exception:
                admin_list_text += f"- `{admin_id}` (يمكن غادر المجموعة)\n"
        await event.reply(admin_list_text)

# --- (مُحَدَّث) أوامر المنشئ ---
@client.on(events.NewMessage(pattern="^(رفع منشئ|تنزيل منشئ|المنشئين|مسح المنشئين|رفع مالك)$"))
async def creator_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action == "رفع مالك":
        if actor_rank < Ranks.OWNER:
            return await event.reply("**فقط المالك الفعلي للمجموعة يستطيع استخدام هذا الأمر.**")
        reply = await event.get_reply_message()
        if not reply:
            return await event.reply(f"**✅ أهلاً بك يا مالك المجموعة!**")
        action = "رفع منشئ"

    if action in ["رفع منشئ", "تنزيل منشئ", "مسح المنشئين"]:
        if actor_rank < Ranks.OWNER:
            return await event.reply("**فقط مالك المجموعة والمطور يستطيعون استخدام هذا الأمر.**")
        
        async with AsyncDBSession() as session:
            if action == "مسح المنشئين":
                await session.execute(delete(Creator).where(Creator.chat_id == event.chat_id))
                await session.commit()
                return await event.reply("**✅ تم مسح قائمة المنشئين لهذه المجموعة بنجاح.**")

            reply = await event.get_reply_message()
            if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
            user_to_manage = await reply.get_sender()
            if user_to_manage.bot: return await event.reply("**لا يمكنك ترقية البوتات.**")
            
            target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
            if target_rank >= actor_rank:
                return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

            result = await session.execute(select(Creator).where(Creator.chat_id == event.chat_id, Creator.user_id == user_to_manage.id))
            is_creator = result.scalar_one_or_none()

            if action == "رفع منشئ":
                if is_creator: return await event.reply("**هذا الشخص هو أصلاً منشئ.**")
                session.add(Creator(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى منشئ في البوت.**")
            else:
                if not is_creator: return await event.reply("**هذا الشخص هو ليس منشئاً أصلاً.**")
                await session.execute(delete(Creator).where(Creator.chat_id == event.chat_id, Creator.user_id == user_to_manage.id))
                await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من المنشئين.**")
            await session.commit()

    elif action == "المنشئين":
        if actor_rank < Ranks.MOD: return
        async with AsyncDBSession() as session:
            result = await session.execute(select(Creator.user_id).where(Creator.chat_id == event.chat_id))
            creator_ids = result.scalars().all()
        
        if not creator_ids: return await event.reply("**لا يوجد أي منشئين في البوت حالياً بهذه المجموعة.**")
        list_text = "**⚜️ قائمة المنشئين في البوت:**\n\n"
        for user_id in creator_ids:
            try:
                user = await client.get_entity(user_id)
                list_text += f"- [{user.first_name}](tg://user?id={user_id})\n"
            except Exception:
                list_text += f"- `{user_id}` (ربما غادر المجموعة)\n"
        await event.reply(list_text)

# --- (مُحَدَّث) أوامر المطور الثانوي ---
@client.on(events.NewMessage(pattern="^(رفع مطور ثانوي|تنزيل مطور ثانوي|المطورين الثانويين|مسح المطورين الثانويين)$"))
async def secondary_dev_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action in ["رفع مطور ثانوي", "تنزيل مطور ثانوي", "مسح المطورين الثانويين"]:
        if actor_rank not in [Ranks.MAIN_DEV, Ranks.OWNER]:
            return await event.reply("**فقط المطور الرئيسي ومالك المجموعة يستطيعون استخدام هذا الأمر.**")
        
        async with AsyncDBSession() as session:
            if action == "مسح المطورين الثانويين":
                await session.execute(delete(SecondaryDev).where(SecondaryDev.chat_id == event.chat_id))
                await session.commit()
                return await event.reply("**✅ تم مسح قائمة المطورين الثانويين لهذه المجموعة بنجاح.**")

            reply = await event.get_reply_message()
            if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
            user_to_manage = await reply.get_sender()
            if user_to_manage.bot: return await event.reply("**لا يمكنك ترقية البوتات.**")
            
            target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
            if target_rank >= actor_rank:
                return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

            result = await session.execute(select(SecondaryDev).where(SecondaryDev.chat_id == event.chat_id, SecondaryDev.user_id == user_to_manage.id))
            is_dev = result.scalar_one_or_none()

            if action == "رفع مطور ثانوي":
                if is_dev: return await event.reply("**هذا الشخص هو أصلاً مطور ثانوي.**")
                session.add(SecondaryDev(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى مطور ثانوي.**")
            else:
                if not is_dev: return await event.reply("**هذا الشخص ليس مطور ثانوي أصلاً.**")
                await session.execute(delete(SecondaryDev).where(SecondaryDev.chat_id == event.chat_id, SecondaryDev.user_id == user_to_manage.id))
                await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من المطورين الثانويين.**")
            await session.commit()

    elif action == "المطورين الثانويين":
        if actor_rank < Ranks.ADMIN: return
        async with AsyncDBSession() as session:
            result = await session.execute(select(SecondaryDev.user_id).where(SecondaryDev.chat_id == event.chat_id))
            dev_ids = result.scalars().all()
        
        if not dev_ids: return await event.reply("**لا يوجد أي مطورين ثانويين في المجموعة.**")
        list_text = "**⚜️ قائمة المطورين الثانويين:**\n\n"
        for user_id in dev_ids:
            try:
                user = await client.get_entity(user_id)
                list_text += f"- [{user.first_name}](tg://user?id={user_id})\n"
            except Exception:
                list_text += f"- `{user_id}` (ربما غادر المجموعة)\n"
        await event.reply(list_text)

# --- (مُحَدَّث) أوامر العضو المميز ---
@client.on(events.NewMessage(pattern="^(رفع مميز|تنزيل مميز|المميزين|مسح المميزين)$"))
async def vip_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    action = event.raw_text
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)

    if action in ["رفع مميز", "تنزيل مميز", "مسح المميزين"]:
        if actor_rank < Ranks.ADMIN:
            return await event.reply("**هذا الأمر للادمنية فما فوق.**")
        
        async with AsyncDBSession() as session:
            if action == "مسح المميزين":
                await session.execute(delete(Vip).where(Vip.chat_id == event.chat_id))
                await session.commit()
                return await event.reply("**✅ تم مسح قائمة الأعضاء المميزين لهذه المجموعة بنجاح.**")

            reply = await event.get_reply_message()
            if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص.**")
            user_to_manage = await reply.get_sender()
            if user_to_manage.bot: return await event.reply("**لا يمكنك ترقية البوتات.**")
            
            target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
            if target_rank >= actor_rank:
                return await event.reply("**لا يمكنك إدارة شخص بنفس رتبتك أو أعلى.**")

            result = await session.execute(select(Vip).where(Vip.chat_id == event.chat_id, Vip.user_id == user_to_manage.id))
            is_vip = result.scalar_one_or_none()

            if action == "رفع مميز":
                if is_vip: return await event.reply("**هذا الشخص هو أصلاً عضو مميز.**")
                session.add(Vip(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**✅ تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى عضو مميز.**")
            else:
                if not is_vip: return await event.reply("**هذا الشخص ليس عضو مميز أصلاً.**")
                await session.execute(delete(Vip).where(Vip.chat_id == event.chat_id, Vip.user_id == user_to_manage.id))
                await event.reply(f"**☑️ تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من المميزين.**")
            await session.commit()

    elif action == "المميزين":
        if actor_rank < Ranks.MOD: return
        async with AsyncDBSession() as session:
            result = await session.execute(select(Vip.user_id).where(Vip.chat_id == event.chat_id))
            vip_ids = result.scalars().all()
        
        if not vip_ids: return await event.reply("**لا يوجد أي أعضاء مميزين في المجموعة.**")
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
    if not await check_activation(event.chat_id): return
    if await get_user_rank(event.sender_id, event.chat_id) < Ranks.MOD:
        return await event.reply("**هذا الأمر متاح للمشرفين فما فوق.**")

    try:
        size = int(event.pattern_match.group(1))
    except (ValueError, IndexError):
        return await event.reply("⚠️ يرجى تحديد رقم صحيح.")

    if not (50 <= size <= 2000):
        return await event.reply("⚠️ حجم الكلايش يجب أن يكون بين 50 و 2000 حرف.")

    await set_chat_setting(event.chat_id, "long_text_size", size)
    await event.reply(f"✅ **تم تحديث الإعدادات بنجاح.**\nسيتم اعتبار أي رسالة أطول من **{size}** حرف 'كليشة'.")


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
