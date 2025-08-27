# plugins/dictionary.py

import asyncio
from telethon import events
from bot import client
from .utils import db, save_db, get_user_rank, Ranks, check_activation
# سنقوم باستيراد قاموس اللهجة العراقية لدمجه في البحث
from slang_data import IRAQI_SLANG

@client.on(events.NewMessage(pattern=r"^معنى (.+)"))
async def combined_define_handler(event):
    """
    Looks up a word first in the local slang dictionary, then in the custom
    user-built dictionary.
    """
    if not await check_activation(event.chat_id): return

    word = event.pattern_match.group(1).strip()
    word_lower = word.lower()

    # الخطوة 1: البحث في قاموس اللهجة العراقية (ملف ثابت)
    if word_lower in IRAQI_SLANG:
        definition = IRAQI_SLANG[word_lower]
        return await event.reply(f"**📖 | معنى كلمة: {word} (لهجة عراقية)**\n\n**{definition}**")

    # الخطوة 2: البحث في القاموس المخصص (من قاعدة البيانات)
    custom_dictionary = db.get("custom_dictionary", {})
    if word_lower in custom_dictionary:
        definition = custom_dictionary[word_lower]
        return await event.reply(f"**📖 | معنى كلمة: {word} (من قاموس البوت)**\n\n**{definition}**")

    # الخطوة 3: إذا لم يتم العثور على الكلمة
    await event.reply(f"**عذراً، لم يتم العثور على تعريف للكلمة '{word}' في قاموس البوت.**")

@client.on(events.NewMessage(pattern="^اضف معنى$"))
async def add_definition_handler(event):
    """
    Handles the conversation to add a new word to the custom dictionary.
    """
    if not await check_activation(event.chat_id): return
    
    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")

    try:
        async with client.conversation(event.chat_id, timeout=180) as conv:
            await conv.send_message("**تمام، لنضف تعريفاً جديداً للقاموس.**\n\n**أرسل الآن الكلمة التي تريد تعريفها:**")
            
            word_msg = await conv.get_response(from_users=event.sender_id)
            word = word_msg.text.strip().lower()

            await conv.send_message(f"**حسناً، الكلمة هي `{word}`.**\n\n**أرسل الآن التعريف الكامل لهذه الكلمة:**")
            
            definition_msg = await conv.get_response(from_users=event.sender_id)
            definition = definition_msg.text.strip()
            
            # الحفظ في قاعدة البيانات
            if "custom_dictionary" not in db:
                db["custom_dictionary"] = {}
            
            db["custom_dictionary"][word] = definition
            save_db(db)
            
            await definition_msg.reply(f"**✅ | تم حفظ تعريف الكلمة `{word}` بنجاح في قاموس البوت.**")

    except asyncio.TimeoutError:
        await event.reply("**⏰ | انتهى الوقت. لقد استغرقت وقتاً طويلاً للرد.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ غير متوقع:**\n`{e}`")

@client.on(events.NewMessage(pattern=r"^حذف معنى (.+)"))
async def delete_definition_handler(event):
    """
    Deletes a word from the custom dictionary.
    """
    if not await check_activation(event.chat_id): return

    user_rank = await get_user_rank(event.sender_id, event)
    if user_rank < Ranks.GROUP_ADMIN:
        return await event.reply("**🚫 | هذا الأمر متاح للمشرفين فما فوق.**")
    
    word_to_delete = event.pattern_match.group(1).strip().lower()
    
    if "custom_dictionary" in db and word_to_delete in db["custom_dictionary"]:
        del db["custom_dictionary"][word_to_delete]
        save_db(db)
        await event.reply(f"**🗑️ | تم حذف الكلمة `{word_to_delete}` من القاموس بنجاح.**")
    else:
        await event.reply(f"**⚠️ | لم أجد الكلمة `{word_to_delete}` في القاموس.**")

@client.on(events.NewMessage(pattern="^القاموس$"))
async def list_dictionary_handler(event):
    """
    Lists all words in the custom dictionary.
    """
    if not await check_activation(event.chat_id): return
    
    custom_dictionary = db.get("custom_dictionary", {})
    
    if not custom_dictionary:
        return await event.reply("**ℹ️ | القاموس المخصص فارغ حالياً. يمكن للمشرفين إضافة كلمات باستخدام أمر `اضف معنى`.**")
        
    reply_text = "**📖 | الكلمات المحفوظة في قاموس البوت:**\n"
    words = "، ".join(f"`{word}`" for word in sorted(custom_dictionary.keys()))
    reply_text += words
    
    await event.reply(reply_text)