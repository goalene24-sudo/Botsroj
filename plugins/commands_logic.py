import logging
import re
import time
import random
import asyncio
from datetime import timedelta
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
from .utils import has_bot_permission, get_user_rank, Ranks, get_rank_name, get_or_create_user, is_command_enabled
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, Vip, User
from .achievements import ACHIEVEMENTS

logger = logging.getLogger(__name__)

# --- دوال مساعدة ---
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
        await session.commit()

# --- قسم منطق الأوامر ---

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
        if not match: 
            return

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
            await session.commit()
            
    except Exception as e:
        logger.error(f"استثناء في lock_unlock_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")


async def kick_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("**بس للمشرفين والكاعدين فوك 👑**")
            
        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")
            
        user_to_kick = await reply.get_sender()
        me = await event.client.get_me()

        if user_to_kick.id == me.id:
            return await event.reply("✦تريدني اطرد نفسي شدتحس بله 😒✦")

        if user_to_kick.id in config.SUDO_USERS:
            return await event.reply("✦دي..ما اكدر اطرد مطوري..دعبل✦")
            
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        actor_rank = await get_user_rank(actor.id, event.chat_id)
        target_rank = await get_user_rank(user_to_kick.id, event.chat_id)
        
        if target_rank >= actor_rank: 
            return await event.reply("**عيب تطرد واحد رتبته اعلى منك او بكدك 😒**")
            
        await event.client.kick_participant(event.chat_id, user_to_kick.id)
        user_mention = f"[{user_to_kick.first_name}](tg://user?id={user_to_kick.id})"
        await event.reply(f"**✈️ | العضو {user_mention} تم طرده بواسطة {actor_mention}**\n\n**- يلا ليشوفنه وجهه بعد 👋**")
        
    except Exception as e:
        logger.error(f"استثناء في kick_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت اطرده، اكو مشكلة 😢:**\n`{e}`")


async def set_rank_logic(event, command_text):
    try:
        rank_map = {
            "رفع ادمن": (Ranks.CREATOR, BotAdmin, "ادمن بالبوت"), "تنزيل ادمن": (Ranks.CREATOR, BotAdmin, "ادمن بالبوت"),
            "رفع منشئ": (Ranks.OWNER, Creator, "منشئ"), "تنزيل منشئ": (Ranks.OWNER, Creator, "منشئ"),
            "رفع مميز": (Ranks.ADMIN, Vip, "عضو مميز"), "تنزيل مميز": (Ranks.ADMIN, Vip, "عضو مميز")
        }
        action = "رفع" if command_text.startswith("رفع") else "تنزيل"
        required_rank, db_model, rank_name = rank_map[command_text]
        
        actor = await event.get_sender()
        actor_rank = await get_user_rank(actor.id, event.chat_id)
        if actor_rank < required_rank: 
            return await event.reply("**على كيفك حبيبي، رتبتك متسمحلك تسوي هيج 🤫**")

        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**رد على رسالة الشخص الي تريد تغير رتبته 😐**")

        user_to_manage = await reply.get_sender()
        if user_to_manage.bot: 
            return await event.reply("**البوتات خارج الخدمة، منكدر نغير رتبتهم 🤖**")

        target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
        if target_rank >= actor_rank: 
            return await event.reply("**عيب والله، تريد تغير رتبة واحد اعلى منك لو بكدك 😒**")

        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        user_mention = f"[{user_to_manage.first_name}](tg://user?id={user_to_manage.id})"

        async with AsyncDBSession() as session:
            result = await session.execute(select(db_model).where(db_model.chat_id == event.chat_id, db_model.user_id == user_to_manage.id))
            is_rank_holder = result.scalar_one_or_none()
            
            if action == "رفع":
                if is_rank_holder: 
                    return await event.reply(f"**يابه هو {user_mention} اصلا {rank_name}، شبيك؟ 😂**")
                session.add(db_model(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**صعدناه ⬆️ | {user_mention} صار {rank_name} بالكروب بأمر من {actor_mention}**")
            else: # تنزيل
                if not is_rank_holder: 
                    return await event.reply(f"**هو اصلاً مو {rank_name} حتى تنزله 🤷‍♂️**")
                await session.delete(is_rank_holder)
                await event.reply(f"**نزلناه ⬇️ | {user_mention} رجع عضو عادي بأمر من {actor_mention}**")
            
            await session.commit()
    except Exception as e:
        logger.error(f"استثناء في set_rank_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

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

async def my_stats_logic(event, command_text):
    try:
        sender = await event.get_sender()
        async with AsyncDBSession() as session:
            user_obj = await get_or_create_user(session, event.chat_id, sender.id)
            inventory = user_obj.inventory or {}
            married_to = inventory.get("married_to")
            best_friend = inventory.get("best_friend")
            gifted_points = inventory.get("gifted_points", 0)
            
            title = None
            custom_title_item = inventory.get("تخصيص لقب")
            if custom_title_item and time.time() - custom_title_item.get("purchase_time", 0) < custom_title_item.get("duration_days", 0) * 86400:
                title = user_obj.custom_title
            if not title:
                vip_item = inventory.get("لقب vip")
                if vip_item and time.time() - vip_item.get("purchase_time", 0) < vip_item.get("duration_days", 0) * 86400:
                    title = "عضو مميز 🎖️"
            
            profile_text = f"**📈 | سجلك يالحبيب [{sender.first_name}](tg://user?id={sender.id})**\n\n"
            if married_to and married_to.get("id") and married_to.get("name"):
                profile_text += f"**❤️ الكبل:** مرتبط ويه [{married_to['name']}](tg://user?id={married_to['id']})\n"
            else:
                profile_text += "**💔 الكبل:** سنكل دايح\n"
            
            if best_friend and best_friend.get("id") and best_friend.get("name"):
                profile_text += f"**🫂 الضلع:** [{best_friend['name']}](tg://user?id={best_friend['id']})\n"
            
            if user_obj.join_date: 
                profile_text += f"**📅 شوكت اجيت:** {user_obj.join_date}\n"
            
            if title: 
                profile_text += f"**🎖️ لقبك:** {title}\n"
            
            profile_text += f"**🎁 شكد داز نقاط:** {gifted_points}\n\n**عاش استمر بالتفاعل يا وحش! ✨**"
        await event.reply(profile_text)
    except Exception as e:
        logger.error(f"استثناء في my_stats_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

async def my_rank_logic(event, command_text):
    try:
        rank_level = await get_user_rank(event.sender_id, event.chat_id)
        rank_name = get_rank_name(rank_level)
        rank_emoji_map = {
            Ranks.MAIN_DEV: "المطور الرئيسي 👨‍💻", Ranks.SECONDARY_DEV: "مطور ثانوي 🛠️", Ranks.OWNER: "المالك 👑",
            Ranks.CREATOR: "المنشئ ⚜️", Ranks.ADMIN: "ادمن بالبوت 🤖", Ranks.MOD: "مشرف 🛡️",
            Ranks.VIP: "شخصية مهمة ✨", Ranks.MEMBER: "عضو عادي 👤"
        }
        emoji = rank_emoji_map.get(rank_level, "عضو 👤")
        await event.reply(f"**رتبتك بالكروب هي: {emoji}**")
    except Exception as e:
        logger.error(f"استثناء في my_rank_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

RANDOM_HEADERS = ["شــوف الحــلو؟ 🧐", "تــعال اشــوفك 🫣", "بــاوع الجــمال 🫠", "تــحبني؟ 🤔", "احــبك ❤️", "هــايروحي 🥹"]
RANDOM_TAFA3UL = ["سايق مخده 🛌", "ياكل تبن 🐐", "نايم بالكروب 😴", "متفاعل نار 🔥", "أسطورة المجموعة 👑", "مدري شيسوي 🤷‍♂️", "يخابر حبيبتة 👩‍❤️‍💋‍👨", "زعطوط الكروب 👶"]

async def id_logic(event, command_text):
    try:
        if not await is_command_enabled(event.chat_id, "id_enabled"): 
            return await event.reply("🚫 | **أمر الايدي واكف هسه بأمر من الادمنية.**")
            
        target_user, replied_msg = None, await event.get_reply_message()
        command_parts = command_text.split(maxsplit=1)
        user_input = command_parts[1] if len(command_parts) > 1 else ""
        
        if replied_msg: 
            target_user = await replied_msg.get_sender()
        elif user_input:
            try: 
                target_user = await client.get_entity(user_input)
            except (ValueError, TypeError): 
                return await event.reply("**منو هذا؟ ما لگيته والله 🤷‍♂️**")
        else: 
            target_user = await event.get_sender()
            
        if not target_user: 
            return await event.reply("**ماعرفت على منو تقصد، وضح اكثر 🤔**")
        
        async with AsyncDBSession() as session:
            user_obj = await get_or_create_user(session, event.chat_id, target_user.id)
            chat = await get_or_create_chat(session, event.chat_id)
            id_photo_enabled = (chat.settings or {}).get("id_photo_enabled", True)
            msg_count = user_obj.msg_count or 0
            points = user_obj.points or 0
            sahaqat = user_obj.sahaqat or 0
            custom_bio = user_obj.bio or "ماكو نبذة، ضيف وحده من الاعدادات 😉"
            user_achievements_keys = user_obj.achievements or []
            inventory = user_obj.inventory or {}

        rank_int = await get_user_rank(target_user.id, event.chat_id)
        rank_map = {
            Ranks.MAIN_DEV: "المطور الرئيسي 👨‍💻", Ranks.SECONDARY_DEV: "مطور ثانوي 🛠️", Ranks.OWNER: "مالك الكروب 👑",
            Ranks.CREATOR: "المنشئ ⚜️", Ranks.ADMIN: "ادمن بالبوت 🤖", Ranks.MOD: "مشرف بالكروب 🛡️",
            Ranks.VIP: "عضو مميز ✨", Ranks.MEMBER: "عضو عادي 👤"
        }
        rank = rank_map.get(rank_int, "عضو 👤")
        badges_str = "".join(ACHIEVEMENTS[key]["icon"] for key in user_achievements_keys if key in ACHIEVEMENTS)
        
        header = random.choice(RANDOM_HEADERS)
        tafa3ul = random.choice(RANDOM_TAFA3UL)
        
        caption = f"**{header}**\n\n"
        caption += f"**⚜️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ ⚜️**\n"
        caption += f"**- آيدي:** `{target_user.id}`\n"
        caption += f"**- يوزرك:** @{target_user.username or 'ما عنده'}\n"
        caption += f"**- اسمك:** [{target_user.first_name}](tg://user?id={target_user.id})\n"
        caption += f"**- رتبتك:** {rank}\n"
        caption += f"**- نبذتك:** {custom_bio}\n"
        caption += f"**- تفاعلك:** {tafa3ul}\n"
        caption += f"**- رسائلك:** `{msg_count}`\n"
        caption += f"**- سحكاتك:** `{sahaqat}`\n"
        caption += f"**- نقاطك:** `{points}`\n"
        if badges_str: 
            caption += f"**- أوسمتك:** {badges_str}\n"
        caption += f"**⚜️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ ⚜️**"
        
        pfp = None
        if id_photo_enabled: 
            pfp = await client.get_profile_photos(target_user, limit=1)
        if pfp: 
            await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
        else: 
            await event.reply(caption, reply_to=event.id)
            
    except Exception as e:
        logger.error(f"استثناء في id_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

async def get_rules_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            rules = (chat.settings or {}).get("rules")
        if rules: 
            await event.reply(f"**📜 | قوانين الكروب مالتنه:**\n\n**{rules}**")
        else: 
            await event.reply("**الادمنية بعدهم ممخلين قوانين للكروب 🤷‍♂️**")
    except Exception as e:
        logger.error(f"استثناء في get_rules_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

async def toggle_id_photo_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("**بس الادمنية يكدرون يسوون هيج 😉**")
        
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        action = "تشغيل" if command_text.startswith("تشغيل") else "تعطيل"
        
        if action == "تشغيل":
            await set_chat_setting(event.chat_id, "id_photo_enabled", True)
            await event.reply(f"**🖼️ | خوش، من اليوم ورايح الصور تطلع بأمر ايدي بأمر من {actor_mention}**")
        else:
            await set_chat_setting(event.chat_id, "id_photo_enabled", False)
            await event.reply(f"**✖️ | ماشي، بعد ماكو صور بأمر ايدي بأمر من {actor_mention}**")
            
    except Exception as e:
        logger.error(f"استثناء في toggle_id_photo_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماعرف شنو السبب 😢، حاول مرة لخ.**")

async def tag_all_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("**بس المشرفين يكدرون يصيحون الكل 📣**")
            
        msg = await event.reply("**📣 | دا احضر النداء، لحظة...**")
        text = command_text.replace("نداء", "", 1).strip() or "تعالو كلكم بسرعة!"
        users_text = f"**📢 | {text}**\n\n"
        
        participants = await client.get_participants(event.chat_id)
        for user in participants:
            if not user.bot:
                mention = f"• [{user.first_name}](tg://user?id={user.id})\n"
                if len(users_text + mention) > 4000:
                    await client.send_message(event.chat_id, users_text)
                    users_text = ""
                    await asyncio.sleep(1) 
                users_text += mention
                
        if users_text.strip() != f"**📢 | {text}**\n\n":
            await client.send_message(event.chat_id, users_text)
            
        await msg.delete()
        
    except Exception as e:
        await msg.edit(f"**ماكدرت اسوي نداء، صارت مشكلة 😢:**\n`{e}`**")
        logger.error(f"استثناء في tag_all_logic: {e}", exc_info=True)

# --- (تمت الإضافة) دالة جديدة لفك الكتم ---
async def unmute_logic(event, command_text):
    try:
        if not await has_bot_permission(event): 
            return await event.reply("**بس للمشرفين والكاعدين فوك 👑**")
        
        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**رد على رسالة الشخص الي تريد تفك الكتم عنه 🧐**")
        
        user_to_unmute = await reply.get_sender()
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        user_mention = f"[{user_to_unmute.first_name}](tg://user?id={user_to_unmute.id})"

        # فك الكتم باستخدام تيليثون
        await client.edit_permissions(event.chat_id, user_to_unmute.id, send_messages=True)

        # تحديث قاعدة البيانات
        async with AsyncDBSession() as session:
            result = await session.execute(select(User).where(User.chat_id == event.chat_id, User.user_id == user_to_unmute.id))
            user_obj = result.scalar_one_or_none()
            if user_obj:
                user_obj.warns = 0
                user_obj.mute_end_time = None
                await session.commit()
        
        await event.reply(f"**✅ | تم فك الكتم عن {user_mention} بواسطة {actor_mention}**\n\n**- هسه يكدر يرجع يسولف طبيعي.**")

    except Exception as e:
        logger.error(f"Error in unmute_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت افك الكتم، اكو مشكلة 😢:**\n`{e}`")
