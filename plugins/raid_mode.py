import logging
from telethon import events, Button
from telethon.tl.types import ChatBannedRights

from bot import client
from database import AsyncDBSession
from models import Chat
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from .utils import is_admin, get_or_create_chat

logger = logging.getLogger(__name__)

# --- دالة مساعدة للتحقق إذا كان وضع الحماية فعالاً ---
async def is_raid_mode_active(chat_id):
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, chat_id)
        return (chat.settings or {}).get("raid_mode_enabled", False)

# --- معالج أمر تفعيل/إيقاف وضع الحماية ---
@client.on(events.NewMessage(pattern=r"^[!/](وضع الحماية|الوضع الامن) (تفعيل|ايقاف)$"))
async def toggle_raid_mode(event):
    if event.is_private:
        return
        
    if not await is_admin(client, event.chat_id, event.sender_id):
        return await event.reply("**🔒 | هذا الأمر للمشرفين فقط.**")

    action = event.pattern_match.group(2)
    new_state = True if action == "تفعيل" else False

    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        if chat.settings is None:
            chat.settings = {}
        
        new_settings = chat.settings.copy()
        new_settings['raid_mode_enabled'] = new_state
        chat.settings = new_settings
        flag_modified(chat, "settings")
        await session.commit()

    if new_state:
        await event.reply("**✅ | تم تفعيل وضع الحماية من الاقتحام.**\nسيتم تقييد أي عضو جديد حتى يثبت أنه ليس بوت.")
    else:
        await event.reply("**☑️ | تم إيقاف وضع الحماية من الاقتحام.**")

# --- معالج انضمام الأعضاء الجدد عند تفعيل وضع الحماية ---
async def handle_raid_mode_join(event):
    try:
        # 1. تقييد المستخدم الجديد (منعه من إرسال أي شيء)
        await client.edit_permissions(event.chat_id, event.user_id, until_date=None, 
                                      send_messages=False, send_media=False, send_stickers=False,
                                      send_gifs=False, send_games=False, send_inline=False,
                                      send_polls=False, change_info=False, invite_users=False,
                                      pin_messages=False)

        # 2. إرسال رسالة التحقق مع الزر
        user = await event.get_user()
        user_mention = f"[{user.first_name}](tg://user?id={user.id})"
        
        welcome_text = (
            f"**أهلاً بك {user_mention}!**\n\n"
            "**🔒 | المجموعة مؤمنة حالياً. لإلغاء تقييدك والتأكد من أنك لست روبوتاً، يرجى الضغط على الزر أدناه.**"
        )
        
        button = Button.inline("✅ اضغط هنا لإثبات أنك إنسان", data=f"unmute_{event.user_id}")
        await event.reply(welcome_text, buttons=button)

    except Exception as e:
        logger.error(f"Error in handle_raid_mode_join for user {event.user_id}: {e}")

# --- معالج ضغطة زر التحقق ---
@client.on(events.CallbackQuery(pattern=b"^unmute_"))
async def unmute_button_handler(event):
    target_user_id = int(event.data.decode().split('_')[1])
    
    # التأكد من أن الشخص الذي يضغط على الزر هو نفس العضو الجديد
    if event.sender_id != target_user_id:
        return await event.answer("🚫 | هذا الزر مخصص للعضو الجديد فقط.", alert=True)

    try:
        # إزالة كل القيود عن المستخدم
        await client.edit_permissions(event.chat_id, target_user_id, send_messages=True, send_media=True,
                                      send_stickers=True, send_gifs=True, send_games=True,
                                      send_inline=True, send_polls=True)

        await event.edit("**✅ | شكراً لك! تم التحقق بنجاح، يمكنك الآن المشاركة في المجموعة.**", buttons=None)
        await event.answer("تم فك التقييد!")
        
    except Exception as e:
        logger.error(f"Error in unmute_button_handler for user {target_user_id}: {e}")
        await event.answer("حدث خطأ. يرجى الطلب من أحد المشرفين إزالة تقييدك يدوياً.", alert=True)