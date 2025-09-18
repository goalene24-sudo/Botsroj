import logging
import re
import time
import random
import asyncio
from datetime import timedelta
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin, ChannelParticipantsAdmins

from bot import client
import config
from .utils import has_bot_permission, get_user_rank, Ranks, get_rank_name, get_or_create_user, is_command_enabled
from database import AsyncDBSession
from models import Chat, BotAdmin, Creator, Vip, User, SecondaryDev
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

async def set_rank_logic(event, command_text):
    try:
        client = event.client # نحصل على client
        rank_map = {
            "رفع ادمن": (Ranks.CREATOR, BotAdmin, "ادمن بالبوت"), "تنزيل ادمن": (Ranks.CREATOR, BotAdmin, "ادمن بالبوت"),
            "رفع منشئ": (Ranks.OWNER, Creator, "منشئ"), "تنزيل منشئ": (Ranks.OWNER, Creator, "منشئ"),
            "رفع مميز": (Ranks.ADMIN, Vip, "عضو مميز"), "تنزيل مميز": (Ranks.ADMIN, Vip, "عضو مميز")
        }
        action = "رفع" if command_text.startswith("رفع") else "تنزيل"
        required_rank, db_model, rank_name = rank_map[command_text]
        
        actor = await event.get_sender()
        # --- تم التعديل هنا ---
        actor_rank = await get_user_rank(client, actor.id, event.chat_id)
        if actor_rank < required_rank: 
            return await event.reply("**على كيفك حبيبي، رتبتك متسمحلك تسوي هيج 🤫**")

        reply = await event.get_reply_message()
        if not reply: 
            return await event.reply("**رد على رسالة الشخص الي تريد تغير رتبته 😐**")

        user_to_manage = await reply.get_sender()
        if user_to_manage.bot: 
            return await event.reply("**البوتات خارج الخدمة، منكدر نغير رتبتهم 🤖**")

        # --- تم التعديل هنا ---
        target_rank = await get_user_rank(client, user_to_manage.id, event.chat_id)
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
        client = event.client # نحصل على client
        # --- تم التعديل هنا ---
        rank_level = await get_user_rank(client, event.sender_id, event.chat_id)
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
        client = event.client # نحصل على client
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
            id_photo_enabled = (chat.settings or {}).get("show_id_photo", True)
            msg_count = user_obj.msg_count or 0
            points = user_obj.points or 0
            sahaqat = user_obj.sahaqat or 0
            custom_bio = user_obj.bio or "ماكو نبذة، ضيف وحده من الاعدادات 😉"
            user_achievements_keys = user_obj.achievements or []
            inventory = user_obj.inventory or {}

        # --- تم التعديل هنا ---
        rank_int = await get_user_rank(client, target_user.id, event.chat_id)
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
            try:
                pfp = await client.get_profile_photos(target_user, limit=1)
            except Exception:
                pfp = None
                
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

async def tag_all_logic(event, command_text):
    try:
        client = event.client # نحصل على client
        # --- تم التعديل هنا ---
        if not await has_bot_permission(client, event): 
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

async def list_admins_logic(event, command_text):
    try:
        client = event.client # نحصل على client
        msg = await event.reply("جاي احسب الكادر... 📊")

        owner_text, dev_text, tg_admins_text, bot_admins_text, vips_text = "", "", "", "", ""

        main_dev_ids = config.SUDO_USERS
        
        async with AsyncDBSession() as session:
            sec_devs_res = await session.execute(select(SecondaryDev).where(SecondaryDev.chat_id == event.chat_id))
            secondary_dev_ids = [dev.user_id for dev in sec_devs_res.scalars().all()]
            
            all_dev_ids = main_dev_ids + [dev_id for dev_id in secondary_dev_ids if dev_id not in main_dev_ids]

            for dev_id in all_dev_ids:
                try:
                    user = await client.get_entity(dev_id)
                    role = "(الرئيسي)" if dev_id in main_dev_ids else ""
                    dev_text += f"• [{user.first_name}](tg://user?id={user.id}) {role}\n"
                except:
                    dev_text += f"• `{dev_id}`\n"
            
            bot_admins_res = await session.execute(select(BotAdmin).where(BotAdmin.chat_id == event.chat_id))
            for admin in bot_admins_res.scalars().all():
                try:
                    user = await client.get_entity(admin.user_id)
                    bot_admins_text += f"• [{user.first_name}](tg://user?id={user.id})\n"
                except:
                    bot_admins_text += f"• `{admin.user_id}`\n"
            
            vips_res = await session.execute(select(Vip).where(Vip.chat_id == event.chat_id))
            for vip in vips_res.scalars().all():
                try:
                    user = await client.get_entity(vip.user_id)
                    vips_text += f"• [{user.first_name}](tg://user?id={user.id})\n"
                except:
                    vips_text += f"• `{vip.user_id}`\n"

        tg_participants = await client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)
        for p in tg_participants:
            mention = f"• [{p.first_name}](tg://user?id={p.id})\n"
            if isinstance(p.participant, ChannelParticipantCreator):
                owner_text = mention
            else:
                tg_admins_text += mention

        final_text = "⚜️ **قائمة كادر الإدارة بالكروب** ⚜️\n\n"
        if owner_text:
            final_text += f"**👑 مالك المجموعة:**\n{owner_text}\n"
        if dev_text:
            final_text += f"**👨‍💻 مطورين البوت:**\n{dev_text}\n"
        if tg_admins_text:
            final_text += f"**🛡️ المشرفين:**\n{tg_admins_text}\n"
        if bot_admins_text:
            final_text += f"**🤖 الادمنية في البوت:**\n{bot_admins_text}\n"
        if vips_text:
            final_text += f"**✨ المميزين:**\n{vips_text}\n"
        
        if not any([owner_text, dev_text, tg_admins_text, bot_admins_text, vips_text]):
            final_text += "ماكو أي أحد بالكادر حالياً."

        await msg.edit(final_text)

    except Exception as e:
        logger.error(f"Error in list_admins_logic: {e}", exc_info=True)
        await msg.edit("**صارت مشكلة وماكدرت اجيب القائمة 😢**")
