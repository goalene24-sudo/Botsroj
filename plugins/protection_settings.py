# --- استدعاء الدوال والمتغيرات المشتركة من الملف المساعد ---
from .protection_helpers import *
# --- (تمت الإضافة هنا) استيراد الأدوات الصحيحة من تيليثون ---
from telethon.tl.functions.messages import EditChatDefaultBannedRightsRequest
from telethon.tl.types import ChatBannedRights

# --- قسم أوامر الإعدادات ---

async def lock_unlock_logic(event, command_text):
    try:
        if not await has_bot_permission(event.client, event):
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
            "التكرار": "سديت التكرار، الي يكرر رسائلة ياخذ كتم 😠",
        }
        UNLOCK_REPLIES = {
            "الصور": "هسه تكدرون دزون صور براحتكم 🏞️", "الروابط": "يلا عادي نشرو روابط 👍",
            "التوجيه": "فتحت التوجيه، وجهو براحتكم ↪️", "المعرف": "يلا عادي دزو معرفات هسه.",
            "الملصقات": "فتحته للملصقات، طلعو إبداعكم 😂", "البوتات": "فتحت اضافه البوتات بس ديرو بالكم 🤔",
            "الدردشه": "فتحت الدردشه سولفو براحتكم 🥰",
            "التكرار": "فتحت التكرار، بس على كيفكم لتلحون 😂",
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

async def set_rules_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
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
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**بس المنشئين والمالك يكدرون يمسحون القوانين 📜**")

        await set_chat_setting(event.chat_id, "rules", None)
        await event.reply("**🗑️ | خوش، مسحت كل القوانين الي جنت حافظها.**")
    except Exception as e:
        logger.error(f"Error in clear_rules_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسح القوانين 😢**")

async def set_warns_limit_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
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
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
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

async def toggle_id_photo_logic(event, command_text):
    try:
        if not await has_bot_permission(event.client, event):
            return await event.reply("**جماعت الأدمنية بس همه يكدرون يغيرون هاي الإعدادات 😉**")

        if command_text == "تشغيل صورة ايدي":
            new_value = True
            action_text = "راح تظهر"
        elif command_text == "تعطيل صورة ايدي":
            new_value = False
            action_text = "راح تختفي"
        else:
            return

        await set_chat_setting(event.chat_id, "show_id_photo", new_value)

        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"

        reply_msg = (
            f"**✅ | صار وتدلل {actor_mention}**\n\n"
            f"**- هسه صورة الايدي {action_text} بأمر `ايدي`.**"
        )
        await event.reply(reply_msg)

    except Exception as e:
        logger.error(f"Error in toggle_id_photo_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت اغير الإعداد 😢**")

async def add_filter_logic(event, command_text):
    if not await has_bot_permission(event.client, event): return
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
    if not await has_bot_permission(event.client, event): return
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
    if not await has_bot_permission(event.client, event): return
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        words = settings.get("filtered_words", [])

    if not words:
        return await event.reply("**قائمة الكلمات الممنوعة فارغة حالياً. كلشي مسموح 😉**")

    message = "**🚫 قائمة الكلمات الممنوعة:**\n\n" + "\n".join(f"- `{word}`" for word in words)
    await event.reply(message)

async def lock_unlock_all_logic(event, action):
    """
    يقوم بتغيير أذونات المجموعة مباشرة لعمل قفل أو فتح حقيقي.
    """
    if not await is_admin(event.client, event.chat_id, event.sender_id):
        return await event.reply("**هذا الأمر حصراً للمشرفين وملاك المجموعة الحقيقيين.**")

    try:
        actor = await event.get_sender()
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})"
        
        if action == "قفل الكل":
            # كائن الصلاحيات الممنوعة
            # True = ممنوع, False = مسموح
            locked_rights = ChatBannedRights(
                until_date=None, send_messages=True, send_media=True,
                send_stickers=True, send_gifs=True, send_games=True,
                send_inline=True, send_polls=True, change_info=False,
                invite_users=False, pin_messages=False
            )
            await client(EditChatDefaultBannedRightsRequest(
                peer=event.chat_id,
                banned_rights=locked_rights
            ))
            reply_msg = f"**🔒 | تم قفل الدردشة بالكامل بواسطة {actor_mention}.**\n\n**- لن يتمكن الأعضاء من إرسال أي شيء.**"
        
        else: # فتح الكل
            # كائن الصلاحيات المسموحة (لا يوجد أي منع)
            unlocked_rights = ChatBannedRights(
                until_date=None, send_messages=False, send_media=False,
                send_stickers=False, send_gifs=False, send_games=False,
                send_inline=False, send_polls=False, change_info=False,
                invite_users=False, pin_messages=False
            )
            await client(EditChatDefaultBannedRightsRequest(
                peer=event.chat_id,
                banned_rights=unlocked_rights
            ))
            reply_msg = f"**🔓 | تم فتح الدردشة بالكامل بواسطة {actor_mention}.**\n\n**- أصبح بإمكان الأعضاء المشاركة مجدداً.**"
            
        await event.reply(reply_msg)

    except Exception as e:
        logger.error(f"Error in lock_unlock_all_logic: {e}", exc_info=True)
        await event.reply("**حدث خطأ. تأكد من أنني مشرف وأمتلك صلاحية `إضافة مشرفين جدد`.**")
