# plugins/aliases.py

import asyncio
from telethon import events
from bot import client
from .utils import db, save_db, get_user_rank, Ranks, check_activation

@client.on(events.NewMessage(pattern="^اضف امر$"))
async def add_alias_handler(event):
    """
    Handles the conversation to add a new command alias.
    """
    if not await check_activation(event.chat_id): return

    # --- فحص الصلاحيات ---
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")

    chat_id_str = str(event.chat_id)
    
    try:
        async with client.conversation(event.sender_id, timeout=300) as conv:
            # --- (تم التصحيح) استخدام علامات الاقتباس الثلاثية ---
            await conv.send_message("""**تمام، لنقم بإضافة اختصار جديد.

**الخطوة 1 من 2:**
**أرسل الآن الأمر الأصلي الذي تريد إنشاء اختصار له (مثال: `ايدي`).**
**""")
            
            original_command_msg = await conv.get_response()
            original_command = original_command_msg.text.strip()

            # --- (تم التصحيح) استخدام علامات الاقتباس الثلاثية ---
            await conv.send_message(f"""**حسناً، الأمر الأصلي هو: `{original_command}`

**الخطوة 2 من 2:**
**أرسل الآن الأمر الجديد (الاختصار) الذي تريده (مثال: `ا`).**
**""")
            
            alias_command_msg = await conv.get_response()
            alias_command = alias_command_msg.text.strip()

            # --- الحفظ في قاعدة البيانات ---
            if chat_id_str not in db: db[chat_id_str] = {}
            if "command_aliases" not in db[chat_id_str]:
                db[chat_id_str]["command_aliases"] = {}

            # التحقق مما إذا كان الاختصار موجوداً بالفعل
            if alias_command in db[chat_id_str]["command_aliases"]:
                await conv.send_message(f"**⚠️ عذراً، الاختصار `{alias_command}` مستخدم بالفعل. حاول مرة أخرى باختصار مختلف.**")
                return

            db[chat_id_str]["command_aliases"][alias_command] = original_command
            save_db(db)

            await conv.send_message(f"**✅ | تم الحفظ بنجاح!**\n\n**الآن عند إرسال `{alias_command}`، سيتم تنفيذ الأمر `{original_command}`.**")

    except asyncio.TimeoutError:
        await event.reply("**⏰ | انتهى الوقت. لقد استغرقت وقتاً طويلاً للرد.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ غير متوقع:**\n`{e}`")


@client.on(events.NewMessage(pattern=r"^حذف امر (.+)$"))
async def delete_alias_handler(event):
    """
    Deletes an existing command alias.
    """
    if not await check_activation(event.chat_id): return

    # --- فحص الصلاحيات ---
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")
    
    chat_id_str = str(event.chat_id)
    alias_to_delete = event.pattern_match.group(1).strip()

    aliases = db.get(chat_id_str, {}).get("command_aliases", {})

    if alias_to_delete in aliases:
        del db[chat_id_str]["command_aliases"][alias_to_delete]
        save_db(db)
        await event.reply(f"**🗑️ | تم حذف الاختصار `{alias_to_delete}` بنجاح.**")
    else:
        await event.reply(f"**⚠️ | لم أجد الاختصار `{alias_to_delete}` في قائمة الأوامر المضافة.**")


@client.on(events.NewMessage(pattern="^الاوامر المضافة$"))
async def list_aliases_handler(event):
    """
    Lists all custom command aliases for the current chat.
    """
    if not await check_activation(event.chat_id): return

    chat_id_str = str(event.chat_id)
    aliases = db.get(chat_id_str, {}).get("command_aliases", {})

    if not aliases:
        return await event.reply("**ℹ️ | لا توجد أي أوامر مضافة (اختصارات) في هذه المجموعة بعد.**")

    reply_text = "**📋 | قائمة الأوامر المضافة (الاختصارات):**\n\n"
    for alias, original in aliases.items():
        reply_text += f"**- `{alias}` ⇜ `{original}`**\n"
    
    await event.reply(reply_text)
