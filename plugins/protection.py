import asyncio
from datetime import datetime, timedelta
from telethon import events, Button
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, get_user_rank, Ranks, get_or_create_chat, get_or_create_user

# --- معالج الكتم المؤقت عبر الأزرار ---
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
        await event.edit(f"**🤫 تم كتم [{user_to_mute_entity.first_name}](tg://user?id={user_id_to_mute}) {duration_text}.**")
    except Exception as e:
        await event.edit(f"**❌ | حدث خطأ أثناء الكتم:**\n`{e}`")


# --- أوامر فلتر الكلمات ---
@client.on(events.NewMessage(pattern=r"^اضف كلمة ممنوعة(?: (.*))?$"))
async def add_filtered_word(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.MOD: return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق.**")

    word = event.pattern_match.group(1)
    if not word:
        return await event.reply("**الأمر يحتاج كلمة. الاستخدام الصحيح:\n`اضف كلمة ممنوعة [الكلمة اللي تريد تمنعها]`**")

    word = word.strip()
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


@client.on(events.NewMessage(pattern=r"^حذف كلمة ممنوعة(?: (.*))?$"))
async def remove_filtered_word(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.MOD: return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق.**")

    word_to_remove = event.pattern_match.group(1)
    if not word_to_remove:
        return await event.reply("**الأمر يحتاج كلمة. الاستخدام الصحيح:\n`حذف كلمة ممنوعة [الكلمة اللي تريد تحذفها]`**")

    word_to_remove = word_to_remove.strip().lower()
    word_found = None

    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        filtered_words = settings.get("filtered_words", [])
        
        for w in filtered_words:
            if w.lower() == word_to_remove:
                word_found = w
                break

        if word_found:
            filtered_words.remove(word_found)
            settings["filtered_words"] = filtered_words
            chat.settings = settings
            flag_modified(chat, "settings")
            await session.commit()
            await event.reply(f"**✅ خوش، حذفت الكلمة '{word_found}' من قائمة الممنوعات.**")
        else:
            await event.reply(f"**الكلمة '{word_to_remove}' هي أصلاً مموجودة بقائمة الممنوعات.**")


@client.on(events.NewMessage(pattern="^الكلمات الممنوعة$"))
async def list_filtered_words(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.MOD: return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق.**")
    
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        words = settings.get("filtered_words", [])

    if not words:
        return await event.reply("**قائمة الكلمات الممنوعة فارغة حالياً. كلشي مسموح 😉**")

    message = "**🚫 قائمة الكلمات الممنوعة:**\n\n" + "\n".join(f"- `{word}`" for word in words)
    await event.reply(message)


# --- المعالج الموحد لأوامر الإدارة ---
@client.on(events.NewMessage(pattern=r"^(حظر|الغاء الحظر|كتم|الغاء الكتم|تحذير|حذف التحذيرات)$"))
async def consolidated_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.MOD:
        return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق. 😒**")

    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو؟ لازم تسوي رپلَي على رسالة الشخص.**")
    
    me = await client.get_me()
    user_to_manage = await reply.get_sender()
    if user_to_manage.id == me.id:
        return await event.reply("**لا يمكنك استخدام هذا الأمر على البوت نفسه.**")
    
    target_rank = await get_user_rank(user_to_manage.id, event.chat_id)
    
    if target_rank >= actor_rank:
        return await event.reply("**ما أگدر أطبق هذا الإجراء على شخص رتبته أعلى منك أو تساوي رتبتك!**")

    action = event.raw_text
    try:
        if action == "حظر":
            await client.edit_permissions(event.chat_id, user_to_manage, view_messages=False)
            await event.reply(f"**🚫 طار [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
        elif action == "الغاء الحظر":
            await client.edit_permissions(event.chat_id, user_to_manage, view_messages=True)
            await event.reply(f"**✅ يلا رجعنا [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
        elif action == "كتم":
            buttons = [
                [Button.inline("ساعة 🕐", data=f"mute_{user_to_manage.id}_60"), Button.inline("يوم 🗓️", data=f"mute_{user_to_manage.id}_1440")],
                [Button.inline("كتم دائم ♾️", data=f"mute_{user_to_manage.id}_0")],
                [Button.inline("إلغاء الأمر ❌", data=f"mute_{user_to_manage.id}_-1")]
            ]
            await event.reply(f"**🤫 تريد تكتم [{user_to_manage.first_name}](tg://user?id={user_to_manage.id})؟ اختار المدة:**", buttons=buttons)
        elif action == "الغاء الكتم":
            await client.edit_permissions(event.chat_id, user_to_manage, send_messages=True)
            await event.reply(f"**🗣️ يلا احچي [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}).**")
        elif action == "تحذير":
            async with AsyncDBSession() as session:
                user_obj = await get_or_create_user(session, event.chat_id, user_to_manage.id)
                chat_obj = await get_or_create_chat(session, event.chat_id)
                
                user_obj.warns = user_obj.warns + 1 if user_obj.warns else 1
                new_warn_count = user_obj.warns
                max_warns = (chat_obj.settings or {}).get("max_warns", 3)
                
                if new_warn_count >= max_warns:
                    until_date = datetime.now() + timedelta(minutes=1440) # 24 hours
                    await client.edit_permissions(event.chat_id, user_to_manage, send_messages=False, until_date=until_date)
                    await event.reply(f"**❗️وصل للحد الأقصى!❗️**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) وصل {new_warn_count}/{max_warns} تحذيرات.**\n\n**تم كتمه تلقائياً لمدة 24 ساعة. 🤫**")
                    user_obj.warns = 0 # Reset warns after punishment
                else:
                    await event.reply(f"**⚠️ تم توجيه تحذير!**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) استلم تحذيراً.**\n\n**صار عنده هسه {new_warn_count}/{max_warns} تحذيرات. دير بالك مرة لخ!**")
                
                await session.commit()
        elif action == "حذف التحذيرات":
            async with AsyncDBSession() as session:
                user_obj = await get_or_create_user(session, event.chat_id, user_to_manage.id)
                if user_obj.warns and user_obj.warns > 0:
                    user_obj.warns = 0
                    await session.commit()
                    await event.reply(f"**✅ تم تصفير العداد.**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) رجع خوش آدمي وما عنده أي تحذير.**")
                else:
                    await event.reply(f"**هذا العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) أصلاً ما عنده أي تحذيرات. 😇**")
    except Exception as e:
        await event.reply(f"**ماگدرت اسويها، اكو مشكلة: `{str(e)}`**")

@client.on(events.NewMessage(pattern=r"^كتم (\d+)\s*([ديس])$"))
async def timed_mute_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    actor_rank = await get_user_rank(event.sender_id, event.chat_id)
    if actor_rank < Ranks.MOD:
        return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق. 😒**")

    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو؟ لازم تسوي رپلَي على رسالة الشخص.**")
    
    me = await client.get_me()
    user_to_mute = await reply.get_sender()
    if user_to_mute.id == me.id:
        return await event.reply("**لا يمكنك استخدام هذا الأمر على البوت نفسه.**")
    
    target_rank = await get_user_rank(user_to_mute.id, event.chat_id)
    if target_rank >= actor_rank:
        return await event.reply("**ما أگدر أطبق هذا الإجراء على شخص رتبته أعلى منك أو تساوي رتبتك!**")
        
    try:
        time_value = int(event.pattern_match.group(1))
        time_unit = event.pattern_match.group(2).lower()
        until_date, duration_text = None, ""
        if time_unit == 'د':
            until_date = datetime.now() + timedelta(minutes=time_value)
            duration_text = f"{time_value} دقايق"
        elif time_unit == 'س':
            until_date = datetime.now() + timedelta(hours=time_value)
            duration_text = f"{time_value} ساعات"
        elif time_unit == 'ي':
            until_date = datetime.now() + timedelta(days=time_value)
            duration_text = f"{time_value} أيام"
        else: return
        
        await client.edit_permissions(event.chat_id, user_to_mute, send_messages=False, until_date=until_date)
        await event.reply(f"**🤫 خوش، [{user_to_mute.first_name}](tg://user?id={user_to_mute.id}) انلصم لمدة {duration_text}.**")
    except Exception as e:
        await event.reply(f"**ماگدرت اسويها، اكو مشكلة: `{str(e)}`**")
