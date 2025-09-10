# plugins/poll.py
import random
from telethon import events
from telethon.errors.rpcerrorlist import PollOptionInvalidError, ForbiddenError
from telethon.tl.types import InputMediaPoll, Poll, PollAnswer
from bot import client
from .utils import check_activation, is_admin

# --- (تم التعديل) تغيير "data" إلى "option" ---
def build_poll_options(options_list):
    """Helper function to build PollAnswer objects."""
    return [PollAnswer(text=option.strip(), option=i.to_bytes(1, 'big')) for i, option in enumerate(options_list)]

@client.on(events.NewMessage(pattern=r"^استفتاء(?:\s|$)([\s\S]*)"))
async def poll_creator(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    # جعل الأمر للمشرفين فقط
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("🚫 | **عذراً، هذا الأمر مخصص للمشرفين فقط.**")
        return

    string = event.pattern_match.group(1).strip()
    reply_to_id = await event.get_reply_message()

    # الحالة الافتراضية إذا لم يتم كتابة شيء
    if not string:
        question = "تحبوني ؟"
        options = ["- ايي 😊✌️", "- لاع 😏😕", "- مادري 🥱🙄"]
        
    # الحالة المخصصة
    else:
        poll_parts = string.split('|')
        if len(poll_parts) < 3:
            await event.reply(
                "**⚠️ | طريقة الاستخدام خاطئة.**\n\n"
                "**اكتب الأمر بالشكل التالي:**\n"
                "`استفتاء السؤال | الخيار الأول | الخيار الثاني`\n\n"
                "**ملاحظة:** يجب أن يكون هناك خياران على الأقل."
            )
            return
            
        question = poll_parts[0].strip()
        options = [opt.strip() for opt in poll_parts[1:] if opt.strip()]

        if len(options) > 10:
            await event.reply("**لا يمكن إنشاء استفتاء بأكثر من 10 خيارات.**")
            return

    try:
        await client.send_message(
            event.chat_id,
            file=InputMediaPoll(
                poll=Poll(
                    id=random.getrandbits(32),
                    question=question,
                    answers=build_poll_options(options)
                )
            ),
            reply_to=reply_to_id
        )
        await event.delete()
    except PollOptionInvalidError:
        await event.reply("**عذراً، يبدو أن أحد الخيارات أو السؤال طويل جدًا.**")
    except ForbiddenError:
        await event.reply("**عذراً، لا أمتلك صلاحية إنشاء استفتاء في هذه المجموعة.**")
    except Exception as e:
        await event.reply(f"**حدث خطأ غير متوقع:**\n`{e}`")
