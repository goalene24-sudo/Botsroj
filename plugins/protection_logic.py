import logging
import re
import time
import random
import asyncio
from datetime import datetime, timedelta

from telethon import events, Button
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
from .utils import has_bot_permission, get_user_rank, Ranks, get_or_create_user
from database import AsyncDBSession
from models import Chat, User

logger = logging.getLogger(__name__)

# --- دوال مساعدة (مجمعة من الملفين) ---
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

# --- قسم أوامر القفل ---

LOCK_TYPES_MAP = {
    "الصور": "photo", "الفيديو": "video", "المتحركه": "gif", "الملصقات": "sticker",
    "الروابط": "url", "المعرف": "username", "التوجيه": "forward", "الملفات": "document",
    "الاغاني": "audio", "الصوت": "voice", "السيلفي": "video_note",
    "الكلايش": "long_text", "الدردشه": "text", "الانلاين": "inline", "البوتات": "bot",
    "الجهات": "contact", "الموقع": "location", "الفشار": "game",
    "الانكليزيه": "english", "التعديل": "edit",
}

async def lock_unlock_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("** جماعت الأدمنية بس همه يكدرون يستخدمون هذا الأمر 😉**")

        match = re.match(r"^(قفل|فتح) (.+)$", command_text)
        if not match: return

        action, target = match.group(1), match.group(2).strip()
        lock_key = LOCK_TYPES_MAP.get(target)

        if not lock_key:
            return await event.reply(f"**شنو هاي `{target}`؟ ماعرفها والله 🧐**")

        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"

        LOCK_REPLIES = {
            "الصور": "بعد محد يكدر يدز صور 😠", "الروابط": "ممنوع نشر الروابط بعد خوش؟ 😉",
            "التوجيه": "سديت التوجيه حتى لتدوخونا 😒", "المعرف": "بعد محد يكدر يدز معرفات هنا 🤫",
            "الملصقات": "كافي ملصقات دوختونا 😠", "البوتات": "ممنوع اضافه بوتات بدون اذني 😡",
            "الدردشه": "قفلت الدردشه محد يحجي بعد 🤫",
        }
        UNLOCK_REPLIES = {
            "الصور": "هسه تكدرون دزون صور براحتكم 🏞️", "الروابط": "يلا عادي نشرو روابط 👍",
            "التوجيه": "فتحت التوجيه، وجهو براحتكم ↪️", "المعرف": "يلا عادي دزو معرفات هسه.",
            "الملصقات": "فتحته للملصقات، طلعو إبداعكم 😂", "البوتات": "فتحت اضافه البوتات بس ديرو بالكم 🤔",
            "الدردشه": "فتحت الدردشه سولفو براحتكم 🥰",
        }

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            if chat.lock_settings is None: chat.lock_settings = {}
            new_lock_settings = chat.lock_settings.copy()
            current_state_is_locked = chat.lock_settings.get(lock_key, False)

            if action == "قفل":
                if current_state_is_locked:
                    return await event.reply(f"**يابه هيه {target} اصلاً مقفولة 😒**")
                new_lock_settings[lock_key] = True
                fun_phrase = LOCK_REPLIES.get(target, f"بعد محد يكدر يستخدم {target} هنا.")
                reply_msg = f"**🔒 | تم قفل {target} بواسطة {actor_mention}**\n\n**- {fun_phrase}**"
                await event.reply(reply_msg)
            else:
                if not current_state_is_locked:
                    return await event.reply(f"**ولك هيه {target} اصلاً مفتوحة شبيك 😂**")
                new_lock_settings[lock_key] = False
                fun_phrase = UNLOCK_REPLIES.get(target, f"يلا عادي استخدموا {target} هسه.")
                reply_msg = f"**🔓 | تم فتح {target} بواسطة {actor_mention}**\n\n**- {fun_phrase}**"
                await event.reply(reply_msg)
            
            chat.lock_settings = new_lock_settings
            flag_modified(chat, "lock_settings")
            await session.commit()
            
    except Exception as e:
        logger.error(f"استثناء في lock_unlock_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

# --- قسم أوامر الطرد والكتم والتحذير ---

async def kick_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("**بس للمشرفين والكاعدين فوك 👑**")
            
        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")
            
        user_to_manage = await reply.get_sender()
        me = await event.client.get_me()

        if user_to_manage.id == me.id:
            return await event.reply("✦تريدني اطرد نفسي شدتحس بله 😒✦")

        if user_to_manage.id in config.SUDO_USERS:
            return await event.reply("✦دي..ما اكدر اطرد مطوري..دعبل✦")
            
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        actor_rank = await get_user_rank(actor.id, event.chat_id)
        target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
        
        if target_rank >= actor_rank: 
            return await event.reply("**عيب تطرد واحد رتبته اعلى منك او بكدك 😒**")
            
        await event.client.kick_participant(event.chat_id, user_to_manage.id)
        user_mention = f"[{user_to_manage.first_name}](tg://user?id={user_to_manage.id})"
        await event.reply(f"**✈️ | العضو {user_mention} تم طرده بواسطة {actor_mention}**\n\n**- يلا ليشوفنه وجهه بعد 👋**")
        
    except Exception as e:
        logger.error(f"استثناء في kick_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت اطرده، اكو مشكلة 😢:**\n`{e}`")


async def unmute_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("**بس للمشرفين والكاعدين فوك 👑**")
        
        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**رد على رسالة الشخص الي تريد تفك الكتم عنه 🧐**")
        
        user_to_manage = await reply.get_sender()
        me = await client.get_me()

        if user_to_manage.id == me.id:
            return await event.reply("**اني اصلا ما انكتل حتى تفك كتمي 😑**")
            
        if user_to_manage.id in config.SUDO_USERS:
            return await event.reply("**المطور خط أحمر 😠**")

        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        user_mention = f"[{user_to_manage.first_name}](tg://user?id={user_to_manage.id})"

        await client.edit_permissions(event.chat_id, user_to_manage.id, send_messages=True)

        async with AsyncDBSession() as session:
            result = await session.execute(select(User).where(User.chat_id == event.chat_id, User.user_id == user_to_manage.id))
            user_obj = result.scalar_one_or_none()
            if user_obj:
                user_obj.warns = 0
                user_obj.mute_end_time = None
                await session.commit()
        
        await event.reply(f"**✅ | تم فك الكتم عن {user_mention} بواسطة {actor_mention}**\n\n**- هسه يكدر يرجع يسولف طبيعي.**")

    except Exception as e:
        logger.error(f"Error in unmute_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت افك الكتم، اكو مشكلة 😢:**\n`{e}`")

# --- قسم إعدادات التحذيرات ---

async def set_warns_limit_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**هاي الشغلات بس للمنشئين والمالك 👑**")

        parts = command_text.split()
        if len(parts) < 3 or not parts[2].isdigit():
            return await event.reply("**شكد يعني؟ اكتب الأمر هيج: `ضع عدد التحذيرات 3`**")

        limit = int(parts[2])
        if not 1 <= limit <= 10:
            return await event.reply("**الرقم لازم يكون بين 1 و 10 تحذيرات.**")

        await set_chat_setting(event.chat_id, "max_warns", limit)
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        await event.reply(f"**✅ | صار وتدلل {actor_mention}**\n\n**- هسه العضو الي يوصل `{limit}` تحذيرات راح يتعاقب.**")

    except Exception as e:
        logger.error(f"Error in set_warns_limit_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت اضبط العدد 😢**")

async def set_mute_duration_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**هاي الشغلات بس للمنشئين والمالك 👑**")

        parts = command_text.split()
        if len(parts) < 4 or not parts[3].isdigit():
            return await event.reply("**شكد تريد وقت الكتم؟ اكتب الأمر هيج: `ضع وقت الكتم 6` (يعني 6 ساعات)**")

        duration = int(parts[3])
        if not 1 <= duration <= 168: # 1 hour to 1 week
            return await event.reply("**الوقت لازم يكون بالساعات، بين ساعة وحدة و 168 ساعة (اسبوع).**")

        await set_chat_setting(event.chat_id, "mute_duration_hours", duration)
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        await event.reply(f"**✅ | صار وتدلل {actor_mention}**\n\n**- هسه مدة الكتم التلقائي صارت `{duration}` ساعات.**")

    except Exception as e:
        logger.error(f"Error in set_mute_duration_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت اضبط الوقت 😢**")


# --- أوامر الحظر والكتم والتحذير اليدوية ---

async def ban_logic(event, command_text):
    if not await has_bot_permission(event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")
    
    user_to_manage = await reply.get_sender()
    me = await client.get_me()

    if user_to_manage.id == me.id:
        return await event.reply("✦تريدني احظر نفسي؟ صدك تحجي؟ 😒✦")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")
        
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank: 
        return await event.reply("**عيب تحظر واحد رتبته اعلى منك او بكدك 😒**")

    try:
        await client.edit_permissions(event.chat_id, user_to_manage, view_messages=False)
        await event.reply(f"**🚫 طار [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
    except Exception as e:
        await event.reply(f"**ماكدرت احظره، اكو مشكلة: `{str(e)}`**")

async def unban_logic(event, command_text):
    if not await has_bot_permission(event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")
    
    user_to_manage = await reply.get_sender()
    me = await client.get_me()

    if user_to_manage.id == me.id:
        return await event.reply("✦اني اصلا ما انحظر 😑✦")
            
    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦المطور خط أحمر 😠✦")
        
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank: 
        return await event.reply("**عيب تسوي هيج لواحد رتبته اعلى منك او بكدك 😒**")

    try:
        await client.edit_permissions(event.chat_id, user_to_manage, view_messages=True)
        await event.reply(f"**✅ يلا رجعنا [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
    except Exception as e:
        await event.reply(f"**ماكدرت افك الحظر، اكو مشكلة: `{str(e)}`**")

async def mute_logic(event, command_text):
    if not await has_bot_permission(event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")
    
    user_to_manage = await reply.get_sender()
    me = await client.get_me()

    if user_to_manage.id == me.id:
        return await event.reply("✦صوتي ميطلع؟ غير جاي احجي وياك 😒✦")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")
        
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank: 
        return await event.reply("**عيب تكتم واحد رتبته اعلى منك او بكدك 😒**")
        
    buttons = [
        [Button.inline("ساعة 🕐", data=f"mute_{user_to_manage.id}_60"), Button.inline("يوم 🗓️", data=f"mute_{user_to_manage.id}_1440")],
        [Button.inline("كتم دائم ♾️", data=f"mute_{user_to_manage.id}_0")],
        [Button.inline("إلغاء الأمر ❌", data=f"mute_{user_to_manage.id}_-1")]
    ]
    await event.reply(f"**🤫 تريد تكتم [{user_to_manage.first_name}](tg://user?id={user_to_manage.id})؟ اختار المدة:**", buttons=buttons)


async def warn_logic(event, command_text):
    if not await has_bot_permission(event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")
    
    user_to_manage = await reply.get_sender()
    me = await client.get_me()

    if user_to_manage.id == me.id:
        return await event.reply("✦تحذرني الي؟ والله يا الله 😒✦")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")
        
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank: 
        return await event.reply("**عيب تحذر واحد رتبته اعلى منك او بكدك 😒**")

    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, user_to_manage.id)
        chat_obj = await get_or_create_chat(session, event.chat_id)
        
        user_obj.warns = (user_obj.warns or 0) + 1
        new_warn_count = user_obj.warns
        max_warns = (chat_obj.settings or {}).get("max_warns", 3)
        
        if new_warn_count >= max_warns:
            until_date = datetime.now() + timedelta(days=1)
            await client.edit_permissions(event.chat_id, user_to_manage, send_messages=False, until_date=until_date)
            await event.reply(f"**❗️وصل للحد الأقصى!❗️**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) وصل {new_warn_count}/{max_warns} تحذيرات.**\n\n**تم كتمه تلقائياً لمدة 24 ساعة. 🤫**")
            user_obj.warns = 0
        else:
            await event.reply(f"**⚠️ تم توجيه تحذير!**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) استلم تحذيراً.**\n\n**صار عنده هسه {new_warn_count}/{max_warns} تحذيرات. دير بالك مرة لخ!**")
        
        await session.commit()

async def clear_warns_logic(event, command_text):
    if not await has_bot_permission(event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")

    user_to_manage = await reply.get_sender()
    me = await client.get_me()

    if user_to_manage.id == me.id:
        return await event.reply("✦اني ما عندي تحذيرات اصلاً 😇✦")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦المطور ما عنده تحذيرات يمعود 😑✦")
        
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank: 
        return await event.reply("**عيب تسوي هيج لواحد رتبته اعلى منك او بكدك 😒**")
        
    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, user_to_manage.id)
        if user_obj.warns and user_obj.warns > 0:
            user_obj.warns = 0
            await session.commit()
            await event.reply(f"**✅ تم تصفير العداد.**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) رجع خوش آدمي وما عنده أي تحذير.**")
        else:
            await event.reply(f"**هذا العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) أصلاً ما عنده أي تحذيرات. 😇**")


async def timed_mute_logic(event, command_text):
    if not await has_bot_permission(event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو؟ لازم تسوي رپلَي على رسالة الشخص.**")
    
    user_to_mute = await reply.get_sender()
    me = await client.get_me()

    if user_to_mute.id == me.id:
        return await event.reply("✦صوتي ميطلع؟ غير جاي احجي وياك 😒✦")

    if user_to_mute.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")
        
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    target_rank = await get_user_rank(user_to_mute.id, event.chat_id)
    if target_rank >= actor_rank:
        return await event.reply("**ما أگدر أطبق هذا الإجراء على شخص رتبته أعلى منك أو تساوي رتبتك!**")
        
    try:
        match = re.match(r"^كتم (\d+)\s*([ديس])$", command_text)
        if not match: return
        time_value = int(match.group(1))
        time_unit = match.group(2).lower()
        
        duration_text = ""
        if time_unit == 'د':
            until_date = datetime.now() + timedelta(minutes=time_value)
            duration_text = f"{time_value} دقايق"
        elif time_unit == 'س':
            until_date = datetime.now() + timedelta(hours=time_value)
            duration_text = f"{time_value} ساعات"
        else: return
        
        await client.edit_permissions(event.chat_id, user_to_mute, send_messages=False, until_date=until_date)
        await event.reply(f"**🤫 خوش، [{user_to_mute.first_name}](tg://user?id={user_to_mute.id}) انلصم لمدة {duration_text}.**")
    except Exception as e:
        await event.reply(f"**ماكدرت اسويها، اكو مشكلة: `{str(e)}`**")


# --- قسم الفلترة ---
async def add_filter_logic(event, command_text):
    if not await has_bot_permission(event): return
    word = command_text.replace("اضف كلمة ممنوعة", "").strip()
    if not word:
        return await event.reply("**الأمر يحتاج كلمة. الاستخدام الصحيح:\n`اضف كلمة ممنوعة [الكلمة اللي تريد تمنعها]`**")
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        filtered_words = settings.get("filtered_words", [])
        if word.lower() in [w.lower() for w in filtered_words]:
            return await event.reply(f"**الكلمة '{word}' هي أصلاً ممنوعة يمعود.**")
        
        filtered_words.append(word)
        settings["filtered_words"] = filtered_words
        chat.settings = settings
        flag_modified(chat, "settings")
        await session.commit()
    
    await event.reply(f"**✅ تمام، ضفت الكلمة '{word}' لقائمة الممنوعات.**")

async def remove_filter_logic(event, command_text):
    if not await has_bot_permission(event): return
    word_to_remove = command_text.replace("حذف كلمة ممنوعة", "").strip()
    if not word_to_remove:
        return await event.reply("**الأمر يحتاج كلمة. الاستخدام الصحيح:\n`حذف كلمة ممنوعة [الكلمة اللي تريد تحذفها]`**")
    
    word_to_remove = word_to_remove.lower()
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        filtered_words = settings.get("filtered_words", [])
        
        new_words = [w for w in filtered_words if w.lower() != word_to_remove]

        if len(new_words) < len(filtered_words):
            settings["filtered_words"] = new_words
            chat.settings = settings
            flag_modified(chat, "settings")
            await session.commit()
            await event.reply(f"**✅ خوش، حذفت الكلمة '{word_to_remove}' من قائمة الممنوعات.**")
        else:
            await event.reply(f"**الكلمة '{word_to_remove}' هي أصلاً مموجودة بقائمة الممنوعات.**")
    
async def list_filters_logic(event, command_text):
    if not await has_bot_permission(event): return
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        words = settings.get("filtered_words", [])

    if not words:
        return await event.reply("**قائمة الكلمات الممنوعة فارغة حالياً. كلشي مسموح 😉**")

    message = "**🚫 قائمة الكلمات الممنوعة:**\n\n" + "\n".join(f"- `{word}`" for word in words)
    await event.reply(message)


# --- معالج الكولباك الخاص بأزرار الكتم ---
@client.on(events.CallbackQuery(pattern=b"^mute_"))
async def mute_callback_handler(event):
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.MOD:
        return await event.answer("🚫 | هذا الأمر للمشرفين فقط.", alert=True)

    try:
        data = event.data.decode().split('_')
        user_id_to_mute = int(data[1])
        duration_minutes = int(data[2])
    except (ValueError, IndexError):
        return await event.edit("❌ | بيانات الزر غير صالحة.")

    if duration_minutes == -1: # إلغاء
        return await event.edit("✅ | تم إلغاء أمر الكتم.")

    try:
        user_to_mute_entity = await client.get_entity(user_id_to_mute)
    except Exception:
        return await event.edit("❌ | لا يمكن العثور على المستخدم لكتمه.")

    target_rank = await get_user_rank(user_id_to_mute, event.chat_id)
    if target_rank >= actor_rank:
        return await event.answer("❌ | لا يمكنك كتم شخص رتبته أعلى منك أو تساوي رتبتك!", alert=True)

    until_date = None
    duration_text = "دائم"
    if duration_minutes > 0:
        until_date = datetime.now() + timedelta(minutes=duration_minutes)
        if duration_minutes == 60: duration_text = "لمدة ساعة"
        elif duration_minutes == 1440: duration_text = "لمدة يوم"

    try:
        await client.edit_permissions(event.chat_id, user_to_mute_entity, send_messages=False, until_date=until_date)
        await event.edit(f"**🤫 تم كتم [{user_to_mute_entity.first_name}](tg://user?id={user_to_mute_entity}) {duration_text}.**")
    except Exception as e:
        await event.edit(f"**❌ | حدث خطأ أثناء الكتم:**\n`{e}`")
