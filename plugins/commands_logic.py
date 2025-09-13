import logging
import re
import time
import random
from datetime import timedelta
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from bot import client
from .utils import has_bot_permission, get_user_rank, Ranks, get_rank_name, get_or_create_user, is_command_enabled
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, Vip
from .achievements import ACHIEVEMENTS

logger = logging.getLogger(__name__)

# --- (القسم الأول: منطق القفل والفتح) ---
# ... (الكود السابق يبقى كما هو) ...
LOCK_TYPES_MAP = {
    "الصور": "photo", "الفيديو": "video", "المتحركه": "gif", "الملصقات": "sticker",
    "الروابط": "url", "المعرف": "username", "التوجيه": "forward", "الملفات": "document",
    "الاغاني": "audio", "الصوت": "voice", "السيلفي": "video_note",
    "الكلايش": "long_text", "الدردشه": "text", "الانلاين": "inline", "البوتات": "bot",
    "الجهات": "contact", "الموقع": "location", "الفشار": "game",
    "الانكليزيه": "english", "التعديل": "edit",
}

async def get_or_create_chat(session, chat_id):
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(id=chat_id, settings={}, lock_settings={})
        session.add(chat)
    return chat

async def lock_unlock_logic(event, command_text):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")
        match = re.match(r"^(قفل|فتح) (.+)$", command_text)
        if not match: return 
        action, target = match.group(1), match.group(2).strip()
        lock_key = LOCK_TYPES_MAP.get(target)
        if not lock_key:
            return await event.reply(f"**⚠️ | الأمر `{target}` غير معروف.**")
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            if chat.lock_settings is None: chat.lock_settings = {}
            new_lock_settings, current_state_is_locked = chat.lock_settings.copy(), chat.lock_settings.get(lock_key, False)
            if action == "قفل":
                if current_state_is_locked: return await event.reply(f"**🔒 | {target} مقفلة بالفعل.**")
                new_lock_settings[lock_key] = True
                await event.reply(f"**✅ | تم قفل {target} بنجاح.**")
            else:
                if not current_state_is_locked: return await event.reply(f"**🔓 | {target} مفتوحة بالفعل.**")
                new_lock_settings[lock_key] = False
                await event.reply(f"**✅ | تم فتح {target} بنجاح.**")
            chat.lock_settings = new_lock_settings
            await session.commit()
    except Exception as e:
        logger.error(f"استثناء في lock_unlock_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

# --- (القسم الثاني: منطق الأوامر الإدارية) ---
async def kick_logic(event):
    try:
        if not await has_bot_permission(event):
            return await event.reply("**🚫 | هذا الأمر للمشرفين فما فوق.**")
        reply = await event.get_reply_message()
        if not reply: return await event.reply("**⚠️ | يجب الرد على رسالة.**")
        user_to_kick, actor = await reply.get_sender(), await event.get_sender()
        me = await event.client.get_me()
        if user_to_kick.id in [me.id, actor.id]: return
        actor_rank, target_rank = await get_user_rank(actor.id, event.chat_id), await get_user_rank(user_to_kick.id, event.chat_id)
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

# --- (القسم الثالث: منطق أوامر الملف الشخصي) ---
async def my_stats_logic(event):
    try:
        sender = await event.get_sender()
        async with AsyncDBSession() as session:
            user_obj = await get_or_create_user(session, event.chat_id, sender.id)
            inventory = user_obj.inventory or {}
            married_to, best_friend, gifted_points = inventory.get("married_to"), inventory.get("best_friend"), inventory.get("gifted_points", 0)
            title = None
            custom_title_item = inventory.get("تخصيص لقب")
            if custom_title_item and time.time() - custom_title_item.get("purchase_time", 0) < custom_title_item.get("duration_days", 0) * 86400:
                title = user_obj.custom_title
            if not title:
                vip_item = inventory.get("لقب vip")
                if vip_item and time.time() - vip_item.get("purchase_time", 0) < vip_item.get("duration_days", 0) * 86400:
                    title = "عضو مميز 🎖️"
            profile_text = f"**📈 سجلك الشخصي يا [{sender.first_name}](tg://user?id={sender.id})**\n\n"
            profile_text += f"**❤️ الحالة الاجتماعية:** {'مرتبط/ة بـ [' + married_to.get('name') + '](tg://user?id=' + str(married_to.get('id')) + ')' if married_to else 'أعزب/عزباء'}\n"
            if best_friend: profile_text += f"**🫂 الصديق المفضل:** [{best_friend.get('name')}](tg://user?id={best_friend.get('id')})\n"
            if user_obj.join_date: profile_text += f"**📅 تاريخ الانضمام:** {user_obj.join_date}\n"
            if title: profile_text += f"**🎖️ اللقب:** {title}\n"
            profile_text += f"**🎁 النقاط المهدَاة:** {gifted_points}\n\n**استمر بالتفاعل! ✨**"
        await event.reply(profile_text)
    except Exception as e:
        logger.error(f"استثناء في my_stats_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

async def my_rank_logic(event):
    try:
        rank_level = await get_user_rank(event.sender_id, event.chat_id)
        rank_name = get_rank_name(rank_level)
        rank_emoji_map = {Ranks.MAIN_DEV: "👨‍💻", Ranks.SECONDARY_DEV: "🛠️", Ranks.OWNER: "👑", Ranks.CREATOR: "⚜️", Ranks.ADMIN: "🤖", Ranks.MOD: "🛡️", Ranks.VIP: "✨", Ranks.MEMBER: "👤"}
        emoji = rank_emoji_map.get(rank_level, "👤")
        await event.reply(f"⌔︙**رتبتك هي :** {rank_name} {emoji}")
    except Exception as e:
        logger.error(f"استثناء في my_rank_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")

# --- (تمت الإضافة) القسم الرابع: منطق أمر ايدي ---
RANDOM_HEADERS = ["شــوف الحــلو؟ 🧐", "تــعال اشــوفك 🫣", "بــاوع الجــمال 🫠", "تــحبني؟ 🤔", "احــبك ❤️", "هــايروحي 🥹"]
RANDOM_TAFA3UL = ["سايق مخده 🛌", "ياكل تبن 🐐", "نايم بالكروب 😴", "متفاعل نار 🔥", "أسطورة المجموعة 👑", "مدري شيسوي 🤷‍♂️", "يخابر حبيبتة 👩‍❤️‍💋‍👨", "زعطوط الكروب 👶"]

async def id_logic(event, command_text):
    """منطق أمر ايدي."""
    try:
        if not await is_command_enabled(event.chat_id, "id_enabled"):
            return await event.reply("🚫 | **عذراً، أمر الأيدي معطل في هذه المجموعة حالياً.**")
        
        target_user = None
        replied_msg = await event.get_reply_message()
        command_parts = command_text.split(maxsplit=1)
        user_input = command_parts[1] if len(command_parts) > 1 else ""

        if replied_msg:
            target_user = await replied_msg.get_sender()
        elif user_input:
            try:
                target_user = await client.get_entity(user_input)
            except (ValueError, TypeError):
                return await event.reply("**ما لگيت هيج مستخدم.**")
        else:
            target_user = await event.get_sender()

        if not target_user:
            return await event.reply("**ما گدرت أحدد المستخدم.**")

        async with AsyncDBSession() as session:
            user_obj = await get_or_create_user(session, event.chat_id, target_user.id)
            msg_count, points, sahaqat = user_obj.msg_count, user_obj.points, user_obj.sahaqat
            custom_bio, user_achievements_keys = user_obj.bio, user_obj.achievements or []
            inventory = user_obj.inventory or {}

        rank_int = await get_user_rank(target_user.id, event.chat_id)
        rank_map = {Ranks.MAIN_DEV: "المطور الرئيسي 👨‍💻", Ranks.SECONDARY_DEV: "مطور ثانوي 🛠️", Ranks.OWNER: "مالك المجموعة 👑", Ranks.CREATOR: "المنشئ ⚜️", Ranks.ADMIN: "ادمن في البوت 🤖", Ranks.MOD: "مشرف في المجموعة 🛡️", Ranks.VIP: "عضو مميز ✨", Ranks.MEMBER: "عضو 👤"}
        rank = rank_map.get(rank_int, "عضو 👤")
        
        badges_str = "".join(ACHIEVEMENTS[key]["icon"] for key in user_achievements_keys if key in ACHIEVEMENTS)
        
        vip_status_text, custom_title, decoration = None, None, ""
        
        vip_item = inventory.get("لقب vip")
        if vip_item and time.time() - vip_item.get("purchase_time", 0) < vip_item.get("duration_days", 0) * 86400:
            vip_status_text = "💎 | من كبار الشخصيات VIP"
        custom_title_item = inventory.get("تخصيص لقب")
        if custom_title_item and time.time() - custom_title_item.get("purchase_time", 0) < custom_title_item.get("duration_days", 0) * 86400:
            custom_title = user_obj.custom_title
        decoration_item = inventory.get("زخرفة")
        if decoration_item and time.time() - decoration_item.get("purchase_time", 0) < decoration_item.get("duration_days", 0) * 86400:
            decoration = "✨"
        
        header, tafa3ul = random.choice(RANDOM_HEADERS), random.choice(RANDOM_TAFA3UL)
        
        caption = f"**{header}**\n\n"
        if vip_status_text: caption += f"**{vip_status_text}**\n"
        caption += f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**\n"
        caption += f"**- ايديك:** `{target_user.id}`\n"
        caption += f"**- معرفك:** @{target_user.username or 'لا يوجد'}\n"
        caption += f"**- حسابك:** [{target_user.first_name}](tg://user?id={target_user.id}) {decoration}\n"
        caption += f"**- رتبتك:** {rank}\n"
        if custom_title: caption += f"**- لقبك:** {custom_title}\n"
        caption += f"**- نبذتك:** {custom_bio}\n"
        caption += f"**- تفاعلك:** {tafa3ul}\n"
        caption += f"**- رسائلك:** `{msg_count}`\n"
        caption += f"**- سحكاتك:** `{sahaqat}`\n"
        caption += f"**- نقاطك:** `{points}`\n"
        if badges_str: caption += f"**- أوسمتك:** {badges_str}\n"
        caption += f"**⚡️ ᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐᚐ⚡️**"
        
        pfp = await client.get_profile_photos(target_user, limit=1)
        if pfp:
            await client.send_file(event.chat_id, pfp[0], caption=caption, reply_to=event.id)
        else:
            await event.reply(caption, reply_to=event.id)
    except Exception as e:
        logger.error(f"استثناء في id_logic: {e}", exc_info=True)
        await event.reply("حدث خطأ، جرب مرة أخرى.")
