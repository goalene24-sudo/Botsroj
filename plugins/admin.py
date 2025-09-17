import asyncio
from telethon import events
from bot import client
import json

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from sqlalchemy import delete
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, SecondaryDev, Vip, User

# --- استيراد الدوال والرتب المحدثة ---
from .utils import check_activation, has_bot_permission, get_user_rank, Ranks, build_protection_menu
import logging

logger = logging.getLogger(__name__)

# --- (تمت الإعادة) دوال مساعدة لإدارة إعدادات المجموعة ---
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
        if chat.settings is None:
            chat.settings = {}
        return chat.settings.get(key, default)

async def set_chat_setting(chat_id, key, value):
    """حفظ أو تحديث قيمة إعداد معين في حقل JSON."""
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        if chat.settings is None:
            chat.settings = {}
        
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

# --- الأوامر المتبقية والفريدة لهذا الملف ---

@client.on(events.NewMessage(pattern="^ضع قوانين$"))
async def set_rules_handler(event):
    try:
        if event.is_private or not await check_activation(event.chat_id): return
        if not await has_bot_permission(event):
            return await event.reply("**بس المشرفين والأدمنية يگدرون يغيرون القوانين.**")
        async with client.conversation(event.sender_id, timeout=300) as conv:
            await conv.send_message("**تمام، دزلي هسه قوانين المجموعة الجديدة نصاً كاملاً...**")
            response = await conv.get_response(from_users=event.sender_id)
            await set_chat_setting(event.chat_id, "rules", response.text)
            await conv.send_message("**✅ عاشت ايدك، حفظت القوانين الجديدة للمجموعة.**")
    except asyncio.TimeoutError:
        await event.reply("**تأخرت هواي ومادزيت شي. من تريد تعدل صيحني مرة لخ.**")
    except Exception as e:
        logger.error(f"استثناء في set_rules_handler: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

@client.on(events.NewMessage(pattern="^حذف القوانين$"))
async def delete_rules_handler(event):
    try:
        if event.is_private or not await check_activation(event.chat_id): return
        if not await has_bot_permission(event):
            return await event.reply("**بس المشرفين والأدمنية يگدرون يحذفون القوانين.**")
        
        if await get_chat_setting(event.chat_id, "rules"):
            await del_chat_setting(event.chat_id, "rules")
            await event.reply("**🗑️ خوش، مسحت القوانين. صارت المجموعة بلا قوانين حالياً.**")
        else:
            await event.reply("**هي أصلاً ماكو قوانين حتى أحذفها.**")
    except Exception as e:
        logger.error(f"استثناء في delete_rules_handler: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

@client.on(events.NewMessage(pattern="^(ضع ترحيب|حذف الترحيب)$"))
async def welcome_handler(event):
    try:
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
            async with client.conversation(event.sender_id, timeout=180) as conv:
                await conv.send_message("**تمام، دزلي رسالة الترحيب الجديدة.\n\n💡 ملاحظة:\n`{user}` - لمنشن العضو الجديد.\n`{group}` - لاسم المجموعة.**")
                response = await conv.get_response(from_users=event.sender_id)
                await set_chat_setting(event.chat_id, "welcome_message", response.text)
                await event.client.send_message(event.chat_id, "**✅ عاشت ايدك، حفظت رسالة الترحيب المخصصة.**")
    except asyncio.TimeoutError:
        await event.reply("**تأخرت هواي ومادزيت شي. حاول مرة لخ.**")
    except Exception as e:
        logger.error(f"استثناء في welcome_handler: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

@client.on(events.NewMessage(pattern=r"^(رفع مشرف|تنزيل مشرف)$"))
async def promote_demote_handler(event):
    try:
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
    except Exception as e:
        logger.error(f"استثناء في promote_demote_handler: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

@client.on(events.NewMessage(pattern="^(رفع مطور ثانوي|تنزيل مطور ثانوي|المطورين الثانويين|مسح المطورين الثانويين)$"))
async def secondary_dev_handler(event):
    try:
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
                else: # تنزيل مطور ثانوي
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
    except Exception as e:
        logger.error(f"استثناء في secondary_dev_handler: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

@client.on(events.NewMessage(pattern=r"^ضع حجم الكلايش (\d+)$"))
async def set_long_text_size(event):
    try:
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
    except Exception as e:
        logger.error(f"استثناء في set_long_text_size: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")
