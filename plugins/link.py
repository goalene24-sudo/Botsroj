import logging
from telethon import events
from bot import client

# --- استيراد الدوال المساعدة ---
from .utils import check_activation, is_admin

logger = logging.getLogger(__name__)

@client.on(events.NewMessage(pattern=r"^[!/]الرابط$"))
async def link_handler(event):
    """
    يقوم بإنشاء رابط دعوة للمجموعة ويرسله.
    """
    if event.is_private or not await check_activation(event.chat_id):
        return

    # تم حذف شرط التحقق من المشرف لجعل الأمر متاحاً للجميع
    
    try:
        # التحقق مما إذا كان البوت لديه صلاحية إنشاء روابط
        me = await client.get_me()
        bot_perms = await client.get_permissions(event.chat_id, me.id)
        if not bot_perms.invite_users:
            return await event.reply("**ليس لدي صلاحية إنشاء روابط دعوة في هذه المجموعة.**")

        link = await client.export_chat_invite(event.chat_id)
        await event.reply(f"**تفضل، هذا هو رابط الدعوة للمجموعة:**\n`{link}`")

    except Exception as e:
        logger.error(f"Error in link_handler: {e}", exc_info=True)
        await event.reply(f"**حدث خطأ أثناء إنشاء الرابط:**\n`{e}`")