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
from models import Chat, BotAdmin, Creator, Vip
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

# --- (تم التعديل بالكامل) ---
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

        # --- قواميس الردود باللهجة العراقية ---
        LOCK_REPLIES = {
            "الصور": "بعد محد يكدر يدز صور 😠",
            "الروابط": "ممنوع نشر الروابط بعد خوش؟ 😉",
            "التوجيه": "سديت التوجيه حتى لتدوخونا 😒",
            "المعرف": "بعد محد يكدر يدز معرفات هنا 🤫",
            "الملصقات": "كافي ملصقات دوختونا 😠",
            "البوتات": "ممنوع اضافه بوتات بدون اذني 😡",
            "الدردشه": "قفلت الدردشه محد يحجي بعد 🤫",
        }
        UNLOCK_REPLIES = {
            "الصور": "هسه تكدرون دزون صور براحتكم 🏞️",
            "الروابط": "يلا عادي نشرو روابط 👍",
            "التوجيه": "فتحت التوجيه، وجهو براحتكم ↪️",
            "المعرف": "يلا عادي دزو معرفات هسه.",
            "الملصقات": "فتحته للملصقات، طلعو إبداعكم 😂",
            "البوتات": "فتحت اضافه البوتات بس ديرو بالكم 🤔",
            "الدردشه": "فتحت الدردشه سولفو براحتكم 🥰",
        }

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            if chat.lock_settings is None: 
                chat.lock_settings = {}
                
            new_lock_settings = chat.lock_settings.copy()
            current_state_is_locked = chat.lock_settings.get(lock_key, False)

            if action == "قفل":
                if current_state_is_locked:
                    return await event.reply(f"**يابه هيه {target} اصلاً مقفولة 😒**")
                
                new_lock_settings[lock_key] = True
                fun_phrase = LOCK_REPLIES.get(target, f"بعد محد يكدر يستخدم {target} هنا.")
                reply_msg = f"**🔒 | تم قفل {target} بواسطة {actor_mention}**\n\n**- {fun_phrase}**"
                await event.reply(reply_msg)
            else: # "فتح"
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
            return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")
            
        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**⚠️ | يجب الرد على رسالة.**")
            
        user_to_kick = await reply.get_sender()
        me = await event.client.get_me()

        if user_to_kick.id == me.id:
            return await event.reply("✦تريدني اطرد نفسي شدتحس بله 😒✦")

        if user_to_kick.id in config.SUDO_USERS:
            return await event.reply("✦دي..ما اكدر اطرد مطوري..دعبل✦")
            
        actor = await event.get_sender()
        actor_rank = await get_user_rank(actor.id, event.chat_id)
        target_rank = await get_user_rank(user_to_kick.id, event.chat_id)
        
        if target_rank >= actor_rank: 
            return await event.reply("**❌ | لا يمكنك طرد رتبة أعلى منك أو مساوية لك.**")
            
        await event.client.kick_participant(event.chat_id, user_to_kick.id)
        await event.reply(f"**✅ | تم طرد [{user_to_kick.first_name}](tg://user?id={user_to_kick.id}) بنجاح.**")
        
    except Exception as e:
        logger.error(f"استثناء في kick_logic: {e}", exc_info=True)
        await event.reply(f"**حدث خطأ:**\n`{e}`")

async def set_rank_logic(event, command_text):
    try:
        rank_map = {"رفع ادمن": (Ranks.CREATOR, BotAdmin, "ادمن"), "تنزيل ادمن": (Ranks.CREATOR, BotAdmin, "ادمن"), "رفع منشئ": (Ranks.OWNER, Creator, "منشئ"), "تنزيل منشئ": (Ranks.OWNER, Creator, "منشئ"), "رفع مميز": (Ranks.ADMIN, Vip, "مميز"), "تنزيل مميز": (Ranks.ADMIN, Vip, "مميز")}
        action = "رفع" if command_text.startswith("رفع") else "تنزيل"
        required_rank, db_model, rank_name = rank_map[command_text]
        actor_rank = await get_user_rank(event.sender_id, event.chat_id)
        if actor_rank < required_rank: return await event.reply("**🚫 | رتبتك لا تسمح.**")
        reply = await event.get_reply_message()
        if not reply: return await event.reply("**⚠️ | يجب الرد على شخص.**")
        user_to_manage = await reply.get_sender()
        if user_to_manage.bot: return await event.reply("**لا يمكن تعديل رتب البوتات.**")
        target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
        if target_rank >= actor_rank: return await event.reply("**❌ | لا يمكنك إدارة رتبة أعلى منك أو مساوية لك.**")
        async with AsyncDBSession() as session:
            result = await session.execute(select(db_model).where(db_model.chat_id == event.chat_id, db_model.user_id == user_to_manage.id))
            is_rank_holder = result.scalar_one_or_none()
            if action == "رفع":
                if is_rank_holder: return await event.reply(f"**ℹ️ | بالفعل {rank_name}.**")
                session.add(db_model(chat_id=event.chat_id, user_id=user_to_manage.id))
                await event.reply(f"**✅ | تم رفع [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) إلى {rank_name}.**")
            else:
                if not is_rank_holder: return await event.reply(f"**ℹ️ | ليس {rank_name} أصلاً.**")
                await session.delete(is_rank_holder)
                await event.reply(f"**☑️ | تم تنزيل [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) من رتبة {rank_name}.**")
            await session.commit()
    except Exception as e:
        logger.error(f"استثناء في set_rank_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

async def my_stats_logic(event, command_text):
    try:
        sender = await event.get_sender()
        async with AsyncDBSession() as session:
            user_obj = await get_or_create_user(session, event.chat_id, sender.id)
            inventory = user_obj.inventory or {} # التصحيح: تعريف المخزون أولاً
            married_to, best_friend, gifted_points = inventory.get("married_to"), inventory.get("best_friend"), inventory.get("gifted_points", 0)
            title = None
            custom_title_item = inventory.get("تخصيص لقب")
            if custom_title_item and time.time() - custom_title_item.get("purchase_time", 0) < custom_title_item.get("duration_days", 0) * 86400: title = user_obj.custom_title
            if not title:
                vip_item = inventory.get("لقب vip")
                if vip_item and time.time() - vip_item.get("purchase_time", 0) < vip_item.get("duration_days", 0) * 86400: title = "عضو مميز 🎖️"
            profile_text = f"**📈 سجلك الشخصي يا [{sender.first_name}](tg://user?id={sender.id})**\n\n"
            if married_to and married_to.get("id") and married_to.get("name"):
                profile_text += f"**❤️ الحالة الاجتماعية:** مرتبط/ة بـ [{married_to['name']}](tg://user?id={married_to['id']})\n"
            else:
                profile_text += "**❤️ الحالة الاجتماعية:** أعزب/عزباء\n"
            if best_friend and best_friend.get("id") and best_friend.get("name"):
                profile_text += f"**🫂 الصديق المفضل:** [{best_friend['name']}](tg://user?id={best_friend['id']})\n"
            if user_obj.join_date: profile_text += f"**📅 تاريخ الانضمام:** {user_obj.join_date}\n"
            if title: profile_text += f"**🎖️ اللقب:** {title}\n"
            profile_text += f"**🎁 النقاط المهدَاة:** {gifted_points}\n\n**استمر بالتفاعل! ✨**"
        await event.reply(profile_text)
    except Exception as e:
        logger.error(f"استثناء في my_stats_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

async def my_rank_logic(event, command_text):
    try:
        rank_level = await get_user_rank(event.sender_id, event.chat_id)
        rank_name = get_rank_name(rank_level)
        rank_emoji_map = {Ranks.MAIN_DEV: "👨‍💻", Ranks.SECONDARY_DEV: "🛠️", Ranks.OWNER: "👑", Ranks.CREATOR: "⚜️", Ranks.ADMIN: "🤖", Ranks.MOD: "🛡️", Ranks.VIP: "✨", Ranks.MEMBER: "👤"}
        emoji = rank_emoji_map.get(rank_level, "👤")
        await event.reply(f"⌔︙**رتبتك هي :** {rank_name} {emoji}")
    except Exception as e:
        logger.error(f"استثناء في my_rank_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

RANDOM_HEADERS = ["شــوف الحــلو؟ 🧐", "تــعال اشــوفك 🫣", "بــاوع الجــمال 🫠", "تــحبني؟ 🤔", "احــبك ❤️", "هــايروحي 🥹"]
RANDOM_TAFA3UL = ["سايق مخده 🛌", "ياكل تبن 🐐", "نايم بالكروب 😴", "متفاعل نار 🔥", "أسطورة المجموعة 👑", "مدري شيسوي 🤷‍♂️", "يخابر حبيبتة 👩‍❤️‍💋‍👨", "زعطوط الكروب 👶"]

async def id_logic(event, command_text):
    try:
        if not await is_command_enabled(event.chat_id, "id_enabled"): return await event.reply("🚫 | **عذراً، أمر الأيدي معطل.**")
        target_user, replied_msg = None, await event.get_reply_message()
        command_parts = command_text.split(maxsplit=1)
        user_input = command_parts[1] if len(command_parts) > 1 else ""
        if replied_msg: target_user = await replied_msg.get_sender()
        elif user_input:
            try: target_user = await client.get_entity(user_input)
            except (ValueError, TypeError): return await event.reply("**ما لگيت هيج مستخدم.**")
        else: target_user = await event.get_sender()
        if not target_user: return await event.reply("**ما گدرت أحدد المستخدم.**")
        
        async with AsyncDBSession() as session:
            user_obj = await get_or_create_user(session, event.chat_id, target_user.id)
            chat = await get_or_create_chat(session, event.chat_id)
            id_photo_enabled = (chat.settings or {}).get("id_photo_enabled", True) # التصحيح: جلب الإعداد
            msg_count, points, sahaqat, custom_bio, user_achievements_keys, inventory = user_obj.msg_count, user_obj.points, user_obj.sahaqat, user_obj.bio, user_obj.achievements or [], user_obj.inventory or {}

        rank_int = await get_user_rank(target_user.id, event.chat_id)
        rank_map = {Ranks.MAIN_DEV: "المطور الرئيسي 👨‍💻", Ranks.SECONDARY_DEV: "مطور ثانوي 🛠️", Ranks.OWNER: "مالك المجموعة 👑", Ranks.CREATOR: "المنشئ ⚜️", Ranks.ADMIN: "ادمن في البوت 🤖", Ranks.MOD: "مشرف في المجموعة 🛡️", Ranks.VIP: "عضو مميز ✨", Ranks.MEMBER: "عضو 👤"}
        rank, badges_str = rank_map.get(rank_int, "عضو 👤"), "".join(ACHIEVEMENTS[key]["icon"] for key in user_achievements_keys if key in ACHIEVEMENTS)
        vip_status_text, custom_title, decoration = None, None, ""
        if (inventory.get("لقب vip") or {}) and time.time() - (inventory.get("لقب vip") or {}).get("purchase_time", 0) < (inventory.get("لقب vip") or {}).get("duration_days", 0) * 86400: vip_status_text = "💎 | من كبار الشخصيات VIP"
        if (inventory.get("تخصيص لقب") or {}) and time.time() - (inventory.get("تخصيص لقب") or {}).get("purchase_time", 0) < (inventory.get("تخصيص لقب") or {}).get("duration_days", 0) * 86400: custom_title = user_obj.custom_title
        if (inventory.get("زخرفة") or {}) and time.time() - (inventory.get("زخرفة") or {}).get("purchase_time", 0) < (inventory.get("زخرفة") or {}).get("duration_days", 0) * 86400: decoration = "✨"
        
        header, tafa3ul = random.choice(RANDOM_HEADERS), random.choice(RANDOM_TAFA3UL)
        caption = f"**{header}**\n\n"
        if vip_status_text: caption += f"**{vip_status_text}**\n"
        caption += f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**\n- ايديك:** `{target_user.id}`\n- معرفك:** @{target_user.username or 'لا يوجد'}\n- حسابك:** [{target_user.first_name}](tg://user?id={target_user.id}) {decoration}\n- رتبتك:** {rank}\n"
        if custom_title: caption += f"- لقبك:** {custom_title}\n"
        caption += f"- نبذتك:** {custom_bio}\n- تفاعلك:** {tafa3ul}\n- رسائلك:** `{msg_count}`\n- سحكاتك:** `{sahaqat}`\n- نقاطك:** `{points}`\n"
        if badges_str: caption += f"- أوسمتك:** {badges_str}\n"
        caption += f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**"
        
        pfp = None
        if id_photo_enabled: pfp = await client.get_profile_photos(target_user, limit=1) # التصحيح: استخدام الإعداد
        if pfp: await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
        else: await event.reply(caption, reply_to=event.id)
    except Exception as e:
        logger.error(f"استثناء في id_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

async def get_rules_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            rules = (chat.settings or {}).get("rules")
        if rules: await event.reply(f"**📜 قوانين المجموعة:**\n\n**{rules}**")
        else: await event.reply("**لم يتم وضع قوانين لهذه المجموعة بعد.**")
    except Exception as e:
        logger.error(f"استثناء في get_rules_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

async def toggle_id_photo_logic(event, command_text):
    try:
        if not await has_bot_permission(event): return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")
        action = "تشغيل" if command_text.startswith("تشغيل") else "تعطيل"
        if action == "تشغيل":
            await set_chat_setting(event.chat_id, "id_photo_enabled", True)
            await event.reply("**✅ | تم تشغيل عرض الصورة في أمر ايدي.**")
        else:
            await set_chat_setting(event.chat_id, "id_photo_enabled", False)
            await event.reply("**☑️ | تم تعطيل عرض الصورة في أمر ايدي.**")
    except Exception as e:
        logger.error(f"استثناء في toggle_id_photo_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

async def tag_all_logic(event, command_text):
    try:
        if not await has_bot_permission(event): return await event.reply("**هذا الأمر للمشرفين فقط.**")
        msg = await event.reply("**📣 جاري تحضير النداء...**")
        text = command_text.replace("نداء", "", 1).strip()
        users_text = f"**{text}**\n\n"
        participants = await client.get_participants(event.chat_id)
        for user in participants:
            if not user.bot:
                mention = f"• [{user.first_name}](tg://user?id={user.id})\n"
                if len(users_text + mention) > 4000:
                    await client.send_message(event.chat_id, users_text)
                    users_text = ""
                    await asyncio.sleep(1) 
                users_text += mention
        if users_text.strip(): await client.send_message(event.chat_id, users_text)
        await msg.delete()
    except Exception as e:
        await msg.edit(f"**حدث خطأ أثناء عمل النداء:**\n`{e}`**")
        logger.error(f"استثناء في tag_all_logic: {e}", exc_info=True)
