import logging
import re
import asyncio
from telethon import events
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
from .utils import has_bot_permission, get_user_rank, Ranks
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, Vip

logger = logging.getLogger(__name__)

# --- دوال مساعدة خاصة بهذا الملف ---
async def get_or_create_chat(session, chat_id):
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(id=chat_id, settings={}, lock_settings={})
        session.add(chat)
    return chat

async def set_chat_setting(chat_id, key, value):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        if chat.settings is None: chat.settings = {}
        new_settings = chat.settings.copy()
        new_settings[key] = value
        chat.settings = new_settings
        flag_modified(chat, "settings")
        await session.commit()

async def del_chat_setting(chat_id, key):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        if chat.settings and key in chat.settings:
            new_settings = chat.settings.copy()
            del new_settings[key]
            chat.settings = new_settings
            flag_modified(chat, "settings")
            await session.commit()

# --- قسم إدارة القوانين والترحيب ---
async def set_rules_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**بس المنشئين والمالك يكدرون يخلون قوانين 📜**")

        rules_text = command_text.replace("ضع قوانين", "").strip()
        if not rules_text:
            return await event.reply("**شنو هي القوانين؟ اكتب الأمر وراهه القوانين الي تريدها.**\n\n**مثال: `ضع قوانين ممنوع السب والشتم`**")

        await set_chat_setting(event.chat_id, "rules", rules_text)
        await event.reply("**✅ | صار وتدلل، حفظت القوانين الجديدة للكروب.**")
    except Exception as e:
        logger.error(f"Error in set_rules_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت احفظ القوانين 😢**")

async def clear_rules_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**بس المنشئين والمالك يكدرون يمسحون القوانين 📜**")

        await del_chat_setting(event.chat_id, "rules")
        await event.reply("**🗑️ | خوش، مسحت كل القوانين الي جنت حافظها.**")
    except Exception as e:
        logger.error(f"Error in clear_rules_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسح القوانين 😢**")
        
async def set_welcome_logic(event, command_text):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**بس المشرفين والأدمنية يگدرون يعدلون الترحيب.**")
            
        welcome_text = command_text.replace("ضع ترحيب", "").strip()
        if not welcome_text:
            return await event.reply("**وين الترحيب؟ اكتب الأمر وراه رسالة الترحيب.**\n\n**💡 ملاحظة:\n`{user}` - لمنشن العضو الجديد.\n`{group}` - لاسم المجموعة.**")
            
        await set_chat_setting(event.chat_id, "welcome_message", welcome_text)
        await event.reply("**✅ عاشت ايدك، حفظت رسالة الترحيب المخصصة.**")
    except Exception as e:
        logger.error(f"Error in set_welcome_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت احفظ الترحيب 😢**")

async def clear_welcome_logic(event, command_text):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**بس المشرفين والأدمنية يگدرون يحذفون الترحيب.**")
            
        await del_chat_setting(event.chat_id, "welcome_message")
        await event.reply("**🗑️ خوش، مسحت الترحيب المخصص.**")
    except Exception as e:
        logger.error(f"Error in clear_welcome_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسح الترحيب 😢**")

# --- (جديد) قسم التثبيت ---
async def pin_logic(event, command_text):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**بس المشرفين يكدرون يثبتون رسائل 📌**")
        
        reply = await event.get_reply_message()
        if not reply:
            return await event.reply("**لازم ترد على رسالة حتى اثبتها.**")
            
        # notify=True لإرسال إشعار لأعضاء المجموعة
        await reply.pin(notify=True)
        await event.reply("**📌 | تمام، ثبتت الرسالة.**")
        
    except Exception as e:
        logger.error(f"Error in pin_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت اثبت الرسالة، اكو مشكلة يمكن صلاحياتي ناقصة.**\n`{e}`")

async def unpin_logic(event, command_text):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**بس المشرفين يكدرون يلغون التثبيت 📌**")
            
        await client.pin_message(event.chat_id, message=None, notify=True)
        await event.reply("**🚮 | تمام، لغيت تثبيت كل الرسائل.**")

    except Exception as e:
        logger.error(f"Error in unpin_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت الغي التثبيت، اكو مشكلة يمكن صلاحياتي ناقصة.**\n`{e}`")


# --- قسم عرض ومسح الرتب ---
async def list_bot_admins_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            admins_res = await session.execute(select(BotAdmin).where(BotAdmin.chat_id == event.chat_id))
            admins = admins_res.scalars().all()
        
        if not admins:
            return await event.reply("**ماكو أي ادمن بالبوت حالياً 🤖**")

        text = "**🤖 | قائمة الأدمنية بالبوت:**\n\n"
        for admin in admins:
            try:
                user = await client.get_entity(admin.user_id)
                text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            except:
                text += f"• `{admin.user_id}`\n"
        await event.reply(text)
    except Exception as e:
        logger.error(f"Error in list_bot_admins_logic: {e}", exc_info=True)
        await event.reply("**ماكدرت اجيب قائمة الأدمنية، اكو خطأ صار 😢**")

async def clear_all_bot_admins_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.OWNER:
            return await event.reply("**بس المالك يكدر يسوي هيج شغلة خطيرة 👑**")
        
        async with AsyncDBSession() as session:
            await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == event.chat_id))
            await session.commit()
        
        await event.reply("**🗑️ | تم مسح كل الأدمنية بالبوت.**")
    except Exception as e:
        logger.error(f"Error in clear_all_bot_admins_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسحهم 😢**")

async def list_vips_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            vips_res = await session.execute(select(Vip).where(Vip.chat_id == event.chat_id))
            vips = vips_res.scalars().all()
        
        if not vips:
            return await event.reply("**ماكو أي عضو مميز حالياً ✨**")

        text = "**✨ | قائمة الأعضاء المميزين:**\n\n"
        for vip in vips:
            try:
                user = await client.get_entity(vip.user_id)
                text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            except:
                text += f"• `{vip.user_id}`\n"
        await event.reply(text)
    except Exception as e:
        logger.error(f"Error in list_vips_logic: {e}", exc_info=True)
        await event.reply("**ماكدرت اجيب قائمة المميزين، اكو خطأ صار 😢**")

async def clear_all_vips_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**هاي الشغلة للمنشئين والمالك بس ⚜️**")
        
        async with AsyncDBSession() as session:
            await session.execute(delete(Vip).where(Vip.chat_id == event.chat_id))
            await session.commit()
        
        await event.reply("**🗑️ | تم مسح كل الأعضاء المميزين.**")
    except Exception as e:
        logger.error(f"Error in clear_all_vips_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسحهم 😢**")

async def list_creators_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            creators_res = await session.execute(select(Creator).where(Creator.chat_id == event.chat_id))
            creators = creators_res.scalars().all()
        
        if not creators:
            return await event.reply("**ماكو أي منشئ بالكروب حالياً ⚜️**")

        text = "**⚜️ | قائمة المنشئين بالكروب:**\n\n"
        for creator in creators:
            try:
                user = await client.get_entity(creator.user_id)
                text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            except:
                text += f"• `{creator.user_id}`\n"
        await event.reply(text)
    except Exception as e:
        logger.error(f"Error in list_creators_logic: {e}", exc_info=True)
        await event.reply("**ماكدرت اجيب قائمة المنشئين، اكو خطأ صار 😢**")

async def clear_all_creators_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.OWNER:
            return await event.reply("**بس المالك يكدر يسوي هيج شغلة خطيرة 👑**")
        
        async with AsyncDBSession() as session:
            await session.execute(delete(Creator).where(Creator.chat_id == event.chat_id))
            await session.commit()
        
        await event.reply("**🗑️ | تم مسح كل المنشئين.**")
    except Exception as e:
        logger.error(f"Error in clear_all_creators_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسحهم 😢**")
        
# --- قسم إدارة مشرفي تيليجرام والإعدادات المتقدمة ---
async def promote_demote_logic(event, command_text):
    try:
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
            
        action_map = {"رفع مشرف": True, "تنزيل مشرف": False}
        is_admin_action = action_map.get(command_text)

        try:
            if is_admin_action:
                await client.edit_admin(event.chat_id, user_to_manage, change_info=True, delete_messages=True, ban_users=True, invite_users=True, pin_messages=True)
                await event.reply(f"**✅ | تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى مشرف.**")
            else:
                await client.edit_admin(event.chat_id, user_to_manage, is_admin=False)
                await event.reply(f"**☑️ | تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من الإشراف.**")
        except Exception as e:
            await event.reply(f"**حدث خطأ:**\n`{str(e)}`")
            
    except Exception as e:
        logger.error(f"استثناء في promote_demote_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")
        
async def set_long_text_size_logic(event, command_text):
    try:
        if await get_user_rank(event.sender_id, event.chat_id) < Ranks.MOD:
            return await event.reply("**هذا الأمر متاح للمشرفين فما فوق.**")
            
        try:
            size_str = command_text.replace("ضع حجم الكلايش", "").strip()
            size = int(size_str)
        except (ValueError, IndexError):
            return await event.reply("⚠️ يرجى تحديد رقم صحيح. مثال: `ضع حجم الكلايش 500`")
            
        if not (50 <= size <= 2000):
            return await event.reply("⚠️ حجم الكلايش يجب أن يكون بين 50 و 2000 حرف.")
            
        await set_chat_setting(event.chat_id, "long_text_size", size)
        await event.reply(f"✅ **تم تحديث الإعدادات بنجاح.**\nسيتم اعتبار أي رسالة أطول من **{size}** حرف 'كليشة'.")
        
    except Exception as e:
        logger.error(f"استثناء في set_long_text_size_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")
