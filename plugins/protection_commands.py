from telethon import events, Button
import asyncio

# --- استدعاء الدوال والمتغيرات المشتركة من الملف المساعد ---
from .protection_helpers import *

# --- قسم الأوامر (الإجراءات المباشرة) ---

async def kick_all_bots_logic(event, command_text):
    try:
        # التحقق من رتبة المستخدم (أدمن فما فوق)
        if not await has_bot_permission(event.client, event):
            return await event.reply("**الأدمنية وفوق بس يكدرون يستخدمون هذا الأمر 👑**")

        # التحقق من أن البوت لديه صلاحية الحظر
        try:
            me = await event.client.get_me()
            perms = await event.client.get_permissions(event.chat_id, me.id)
            if not perms.ban_users:
                return await event.reply("**ما عندي صلاحية طرد الأعضاء هنا 😕**")
        except Exception:
            return await event.reply("**ماكدرت اتأكد من صلاحياتي، تأكد أني مشرف.**")

        processing_message = await event.reply("**جاري البحث عن البوتات وطردهم... 🧐**")
        
        kicked_count = 0
        me = await event.client.get_me()

        # المرور على كل أعضاء المجموعة
        async for user in event.client.iter_participants(event.chat_id):
            # التحقق إذا كان المستخدم بوت وليس البوت نفسه
            if user.bot and user.id != me.id:
                try:
                    await event.client.kick_participant(event.chat_id, user.id)
                    kicked_count += 1
                    await asyncio.sleep(1) # تأخير بسيط لتجنب تقييد الحساب
                except Exception as e:
                    logger.error(f"Failed to kick bot {user.id}: {e}")

        if kicked_count > 0:
            await processing_message.edit(f"**✅ | خوش، نظفت الكروب. تم طرد {kicked_count} من البوتات بنجاح.**")
        else:
            await processing_message.edit("**ما لكيت أي بوتات بالكروب حتى اطردها (غيري طبعاً 😉).**")

    except Exception as e:
        logger.error(f"Error in kick_all_bots_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت اكمل طرد البوتات 😢**")


async def kick_logic(event, command_text):
    try:
        if not await has_bot_permission(event.client, event):
            return await event.reply("** جماعت الأدمنية بس همه يكدرون يستخدمون هذا الأمر 😉**")

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
        actor_rank = await get_user_rank(event.client, actor.id, event.chat_id)
        target_rank = await get_user_rank(event.client, user_to_manage.id, event.chat_id)

        if target_rank >= actor_rank:
            return await event.reply("**عيب تطرد واحد رتبته اعلى منك او بكدك 😒**")

        await event.client.kick_participant(event.chat_id, user_to_manage.id)
        user_mention = f"[{user_to_manage.first_name}](tg://user?id={user_to_manage.id})"
        await event.reply(f"**✈️ | العضو {user_mention} تم طرده بواسطة {actor_mention}**\n\n**- يلا ليشوفنه وجهه بعد 👋**")

    except Exception as e:
        logger.error(f"استثناء في kick_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت اطرده، اكو مشكلة 😢:**\n`{e}`")

async def ban_logic(event, command_text):
    if not await has_bot_permission(event.client, event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")

    user_to_manage = await reply.get_sender()

    me = await event.client.get_me()
    if user_to_manage.id == me.id:
        return await event.reply("تريدني احظر نفسي وين صايره هاي🧐")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")

    actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    target_rank = await get_user_rank(event.client, user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank:
        return await event.reply("**عيب تحظر واحد رتبته اعلى منك او بكدك 😒**")

    try:
        await client.edit_permissions(event.chat_id, user_to_manage, view_messages=False)
        await event.reply(f"**🚫 طار [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
    except Exception as e:
        await event.reply(f"**ماكدرت احظره، اكو مشكلة: `{str(e)}`**")

async def unban_logic(event, command_text):
    if not await has_bot_permission(event.client, event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")

    user_to_manage = await reply.get_sender()

    actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    target_rank = await get_user_rank(event.client, user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank:
        return await event.reply("**عيب تسوي هيج لواحد رتبته اعلى منك او بكدك 😒**")

    try:
        await client.edit_permissions(event.chat_id, user_to_manage, view_messages=True)
        await event.reply(f"**✅ يلا رجعنا [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
    except Exception as e:
        await event.reply(f"**ماكدرت افك الحظر، اكو مشكلة: `{str(e)}`**")

async def mute_logic(event, command_text):
    if not await has_bot_permission(event.client, event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")

    user_to_manage = await reply.get_sender()

    me = await event.client.get_me()
    if user_to_manage.id == me.id:
        return await event.reply("هوه اني شوكت حاجي حتى تكتمني.. دعبل😏")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")

    actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    target_rank = await get_user_rank(event.client, user_to_manage.id, event.chat_id)
    if target_rank >= actor_rank:
        return await event.reply("**عيب تكتم واحد رتبته اعلى منك او بكدك 😒**")

    buttons = [
        [Button.inline("ساعة 🕐", data=f"mute_{user_to_manage.id}_60"), Button.inline("يوم 🗓️", data=f"mute_{user_to_manage.id}_1440")],
        [Button.inline("كتم دائم ♾️", data=f"mute_{user_to_manage.id}_0")],
        [Button.inline("إلغاء الأمر ❌", data=f"mute_{user_to_manage.id}_-1")]
    ]
    await event.reply(f"**🤫 تريد تكتم [{user_to_manage.first_name}](tg://user?id={user_to_manage.id})؟ اختار المدة:**", buttons=buttons)

async def unmute_logic(event, command_text):
    try:
        if not await has_bot_permission(event.client, event):
            return await event.reply("**بس للمشرفين والكاعدين فوك 👑**")

        reply = await event.get_reply_message()
        if not reply:
            return await event.reply("**رد على رسالة الشخص الي تريد تفك الكتم عنه 🧐**")

        user_to_manage = await reply.get_sender()

        await client.edit_permissions(event.chat_id, user_to_manage.id, send_messages=True)

        async with AsyncDBSession() as session:
            result = await session.execute(select(User).where(User.chat_id == event.chat_id, User.user_id == user_to_manage.id))
            user_obj = result.scalar_one_or_none()
            if user_obj:
                user_obj.warns = 0
                user_obj.mute_end_time = None
                await session.commit()

        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        user_mention = f"[{user_to_manage.first_name}](tg://user?id={user_to_manage.id})"
        await event.reply(f"**✅ | تم فك الكتم عن {user_mention} بواسطة {actor_mention}**\n\n**- هسه يكدر يرجع يسولف طبيعي.**")

    except Exception as e:
        logger.error(f"Error in unmute_logic: {e}", exc_info=True)
        await event.reply(f"**ماكدرت افك الكتم، اكو مشكلة 😢:**\n`{e}`")

async def warn_logic(event, command_text):
    if not await has_bot_permission(event.client, event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")

    user_to_manage = await reply.get_sender()

    me = await event.client.get_me()
    if user_to_manage.id == me.id:
        return await event.reply("تحذرني الي؟ والله يا الله 😒")

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")

    actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    target_rank = await get_user_rank(event.client, user_to_manage.id, event.chat_id)
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
    if not await has_bot_permission(event.client, event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو بالضبط؟ رد على رسالته علمود اعرفه 🧐**")

    user_to_manage = await reply.get_sender()

    if user_to_manage.id in config.SUDO_USERS:
        return await event.reply("✦المطور ما عنده تحذيرات يمعود 😑✦")

    actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    target_rank = await get_user_rank(event.client, user_to_manage.id, event.chat_id)
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
    if not await has_bot_permission(event.client, event): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو؟ لازم تسوي رپلَي على رسالة الشخص.**")

    user_to_mute = await reply.get_sender()

    if user_to_mute.id in config.SUDO_USERS:
        return await event.reply("✦ما أگدر أطبق هذا الأمر على مطوري..دعبل✦")

    actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
    target_rank = await get_user_rank(event.client, user_to_mute.id, event.chat_id)
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


@client.on(events.CallbackQuery(pattern=b"^mute_"))
async def mute_callback_handler(event):
    client = event.client
    actor_rank = await get_user_rank(client, event.sender_id, event.chat_id)
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

    target_rank = await get_user_rank(client, user_id_to_mute, event.chat_id)
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
        await event.edit(f"**🤫 تم كتم [{user_to_mute_entity.first_name}](tg://user?id={user_to_mute_entity.id}) {duration_text}.**")
    except Exception as e:
        await event.edit(f"**❌ | حدث خطأ أثناء الكتم:**\n`{e}`")
