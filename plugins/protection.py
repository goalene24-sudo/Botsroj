import asyncio
import re
from datetime import datetime, timedelta
from telethon import events, Button
from bot import client
from .utils import check_activation, db, save_db, get_user_rank, Ranks

# --- إعدادات نظام التحذيرات ---
MAX_WARNS = 3
MUTE_DURATION_ON_MAX_WARNS = 1440

# --- دوال مساعدة لنظام التحذيرات ---
def add_user_warn(chat_id, user_id):
    chat_id_str, user_id_str = str(chat_id), str(user_id)
    if "warns" not in db.get(chat_id_str, {}): db[chat_id_str]["warns"] = {}
    new_warns = db[chat_id_str]["warns"].get(user_id_str, 0) + 1
    db[chat_id_str]["warns"][user_id_str] = new_warns
    save_db(db)
    return new_warns

def reset_user_warns(chat_id, user_id):
    chat_id_str, user_id_str = str(chat_id), str(user_id)
    if "warns" in db.get(chat_id_str, {}) and user_id_str in db[chat_id_str]["warns"]:
        del db[chat_id_str]["warns"][user_id_str]
        save_db(db)
        return True
    return False

# --- أوامر فلتر الكلمات ---
@client.on(events.NewMessage(pattern=r"^اضف كلمة ممنوعة(?: (.*))?$"))
async def add_filtered_word(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event)
    if actor_rank < Ranks.GROUP_ADMIN: return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق.**")

    word = event.pattern_match.group(1)
    if not word:
        return await event.reply("**الأمر يحتاج كلمة. الاستخدام الصحيح:\n`اضف كلمة ممنوعة [الكلمة اللي تريد تمنعها]`**")

    word = word.strip()
    chat_id_str = str(event.chat_id)

    if "filtered_words" not in db.get(chat_id_str, {}):
        db[chat_id_str]["filtered_words"] = []

    if word.lower() in [w.lower() for w in db[chat_id_str]["filtered_words"]]:
        return await event.reply(f"**الكلمة '{word}' هي أصلاً ممنوعة يمعود.**")
    
    db[chat_id_str]["filtered_words"].append(word)
    save_db(db)
    await event.reply(f"**✅ تمام، ضفت الكلمة '{word}' لقائمة الممنوعات.**")

@client.on(events.NewMessage(pattern=r"^حذف كلمة ممنوعة(?: (.*))?$"))
async def remove_filtered_word(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event)
    if actor_rank < Ranks.GROUP_ADMIN: return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق.**")

    word_to_remove = event.pattern_match.group(1)
    if not word_to_remove:
        return await event.reply("**الأمر يحتاج كلمة. الاستخدام الصحيح:\n`حذف كلمة ممنوعة [الكلمة اللي تريد تحذفها]`**")

    word_to_remove = word_to_remove.strip()
    chat_id_str = str(event.chat_id)
    
    filtered_words = db.get(chat_id_str, {}).get("filtered_words", [])
    
    word_found = None
    for w in filtered_words:
        if w.lower() == word_to_remove.lower():
            word_found = w
            break

    if word_found:
        filtered_words.remove(word_found)
        save_db(db)
        await event.reply(f"**✅ خوش، حذفت الكلمة '{word_found}' من قائمة الممنوعات.**")
    else:
        await event.reply(f"**الكلمة '{word_to_remove}' هي أصلاً مموجودة بقائمة الممنوعات.**")

@client.on(events.NewMessage(pattern="^الكلمات الممنوعة$"))
async def list_filtered_words(event):
    if event.is_private or not await check_activation(event.chat_id): return
    actor_rank = await get_user_rank(event.sender_id, event)
    if actor_rank < Ranks.GROUP_ADMIN: return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق.**")
    
    chat_id_str = str(event.chat_id)
    words = db.get(chat_id_str, {}).get("filtered_words", [])

    if not words:
        return await event.reply("**قائمة الكلمات الممنوعة فارغة حالياً. كلشي مسموح 😉**")

    message = "**🚫 قائمة الكلمات الممنوعة:**\n\n"
    for word in words:
        message += f"- `{word}`\n"
    
    await event.reply(message)

# --- المعالج الموحد لأوامر الإدارة مع حماية هرمية ---
@client.on(events.NewMessage(pattern=r"^(حظر|الغاء الحظر|كتم|الغاء الكتم|تحذير|حذف التحذيرات)$"))
async def consolidated_admin_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    actor_rank = await get_user_rank(event.sender_id, event)
    if actor_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق. 😒**")

    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو؟ لازم تسوي رپلَي على رسالة الشخص.**")
    
    me = await client.get_me()
    user_to_manage = await reply.get_sender()
    if user_to_manage.id == me.id:
        return await event.reply("**لا يمكنك استخدام هذا الأمر على البوت نفسه.**")
    
    target_rank = await get_user_rank(user_to_manage.id, event)
    
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
            new_warn_count = add_user_warn(event.chat_id, user_to_manage.id)
            if new_warn_count >= MAX_WARNS:
                until_date = datetime.now() + timedelta(minutes=MUTE_DURATION_ON_MAX_WARNS)
                await client.edit_permissions(event.chat_id, user_to_manage, send_messages=False, until_date=until_date)
                await event.reply(f"**❗️وصل للحد الأقصى!❗️**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) وصل {new_warn_count}/{MAX_WARNS} تحذيرات.**\n\n**تم كتمه تلقائياً لمدة 24 ساعة. 🤫**")
                reset_user_warns(event.chat_id, user_to_manage.id)
            else:
                await event.reply(f"**⚠️ تم توجيه تحذير!**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) استلم تحذيراً.**\n\n**صار عنده هسه {new_warn_count}/{MAX_WARNS} تحذيرات. دير بالك مرة لخ!**")
        elif action == "حذف التحذيرات":
            if reset_user_warns(event.chat_id, user_to_manage.id):
                await event.reply(f"**✅ تم تصفير العداد.**\n**العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) رجع خوش آدمي وما عنده أي تحذير.**")
            else:
                await event.reply(f"**هذا العضو [{user_to_manage.first_name}](tg://user?id={user_to_manage.id}) أصلاً ما عنده أي تحذيرات. 😇**")
    except Exception as e:
        await event.reply(f"**ماگدرت اسويها، اكو مشكلة: `{str(e)}`**")

@client.on(events.NewMessage(pattern=r"^كتم (\d+)\s*([ديس])$"))
async def timed_mute_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    actor_rank = await get_user_rank(event.sender_id, event)
    if actor_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**ها وين رايح؟ هاي الشغلة بس للمشرفين فما فوق. 😒**")

    reply = await event.get_reply_message()
    if not reply: return await event.reply("**على منو؟ لازم تسوي رپلَي على رسالة الشخص.**")
    
    me = await client.get_me()
    user_to_mute = await reply.get_sender()
    if user_to_mute.id == me.id:
        return await event.reply("**لا يمكنك استخدام هذا الأمر على البوت نفسه.**")
    
    target_rank = await get_user_rank(user_to_mute.id, event)
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
