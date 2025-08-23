from telethon import events
from bot import client
import config
from .utils import db, save_db

# هذا الجزء يستقبل الرسائل من المستخدمين ويوجهها إليك
@client.on(events.NewMessage(is_private=True, func=lambda e: e.sender_id not in config.SUDO_USERS))
async def forward_to_owner(event):
    try:
        # إعادة توجيه الرسالة إلى أول مطور في القائمة (أنت)
        forwarded_message = await client.forward_messages(config.SUDO_USERS[0], event.message)
        
        # التأكد من وجود قسم لجلسات التواصل في قاعدة البيانات
        if "contact_sessions" not in db:
            db["contact_sessions"] = {}
            
        # حفظ معرف رسالتك الجديدة مع معرف المستخدم الأصلي
        # هذا يسمح للبوت بمعرفة لمن يرد لاحقاً
        db["contact_sessions"][str(forwarded_message.id)] = event.sender_id
        save_db(db)

        # إرسال رسالة تأكيد للمستخدم
        await event.reply("✅ تم إرسال رسالتك إلى المطور، شكراً لتواصلك.")
    except Exception as e:
        print(f"[CONTACT PLUGIN] Failed to forward message from {event.sender_id}. Error: {e}")


# هذا الجزء الجديد يستقبل ردودك ويوجهها للمستخدمين
@client.on(events.NewMessage(is_private=True, from_users=config.SUDO_USERS, func=lambda e: e.is_reply))
async def reply_to_user(event):
    # الحصول على معرف الرسالة التي ترد عليها
    replied_to_id = str(event.reply_to_msg_id)
    
    # التحقق مما إذا كانت هذه الرسالة جزءاً من جلسة تواصل
    contact_sessions = db.get("contact_sessions", {})
    if replied_to_id in contact_sessions:
        user_id = contact_sessions[replied_to_id]
        
        try:
            # إرسال رسالتك (الرد) إلى المستخدم الأصلي
            await client.send_message(user_id, event.message)
            
            # (اختياري) يمكنك جعل البوت يضع علامة (👍) على ردك لتأكيد إرساله
            await event.react('👍')
        except Exception as e:
            await event.reply(f"⚠️ لم أتمكن من إرسال الرد إلى المستخدم. قد يكون قد قام بحظر البوت.\n\n**الخطأ:** `{e}`")

