# plugins/akinator_game.py
import asyncio
import akinator
from telethon import events, Button
from bot import client
from .utils import check_activation

# قاموس لحفظ الألعاب النشطة لكل لاعب
ACTIVE_AKI_GAMES = {}

# دالة لإنشاء أزرار الإجابات
def build_aki_buttons(chat_id, user_id):
    buttons = [
        [
            Button.inline("✅ نعم", data=f"aki_ans:{chat_id}:{user_id}:y"),
            Button.inline("❌ لا", data=f"aki_ans:{chat_id}:{user_id}:n"),
            Button.inline("❓ لا أعرف", data=f"aki_ans:{chat_id}:{user_id}:i"),
        ],
        [
            Button.inline("👍 ربما", data=f"aki_ans:{chat_id}:{user_id}:p"),
            Button.inline("👎 ربما لا", data=f"aki_ans:{chat_id}:{user_id}:pn"),
        ],
        [
            Button.inline("🔙 رجوع للسؤال السابق", data=f"aki_ans:{chat_id}:{user_id}:b"),
        ],
        [
            Button.inline("🚫 إنهاء اللعبة", data=f"aki_ans:{chat_id}:{user_id}:end"),
        ]
    ]
    return buttons

@client.on(events.NewMessage(pattern="^اكيناتور$"))
async def start_akinator(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    chat_id = event.chat_id
    user_id = event.sender_id
    game_key = (chat_id, user_id)

    if game_key in ACTIVE_AKI_GAMES:
        await event.reply("**لديك لعبة اكيناتور نشطة بالفعل! أكملها أولاً أو قم بإنهائها.**")
        return

    zed = await event.reply("`جارِ استدعاء المارد... 🧞`")
    
    try:
        aki = akinator.Akinator()
        # بدء اللعبة باللغة العربية
        q = await aki.start_game(language='ar', child_mode=True)
        
        game_state = {
            "aki": aki,
            "question": q,
            "message_id": None,
        }
        
        buttons = build_aki_buttons(chat_id, user_id)
        msg = await zed.edit(f"**🧞‍♂️ | المارد يسأل:**\n\n**- {q}**", buttons=buttons)
        
        game_state["message_id"] = msg.id
        ACTIVE_AKI_GAMES[game_key] = game_state

    except Exception as e:
        await zed.edit(f"**عذرًا، حدث خطأ أثناء بدء اللعبة:**\n`{e}`")


@client.on(events.CallbackQuery(pattern=b"aki_ans:(.*)"))
async def handle_akinator_answer(event):
    data_str = event.data.decode('utf-8')
    _, chat_id_str, user_id_str, answer = data_str.split(':')
    
    chat_id = int(chat_id_str)
    user_id = int(user_id_str)

    if event.sender_id != user_id:
        await event.answer("🚫 | هذه اللعبة ليست لك!", alert=True)
        return

    game_key = (chat_id, user_id)

    if game_key not in ACTIVE_AKI_GAMES:
        await event.answer("هذه اللعبة قد انتهت أو تم حذفها.", alert=True)
        await event.edit("`تم إنهاء هذه اللعبة.`")
        return
        
    game_state = ACTIVE_AKI_GAMES[game_key]
    aki = game_state["aki"]
    
    if answer == "end":
        del ACTIVE_AKI_GAMES[game_key]
        await event.edit("**🧞‍♂️ | تم إنهاء اللعبة بناءً على طلبك.**")
        return
        
    await event.edit("`جاري تحليل إجابتك...`")
    
    try:
        if answer == "b":
            # الرجوع للسؤال السابق
            q = await aki.back()
        else:
            # إرسال الإجابة
            q = await aki.answer(answer)

        if aki.progression >= 80:
            await aki.win()
            guess = aki.first_guess
            
            # بناء الرسالة النهائية
            result_text = (
                f"**🧞‍♂️ | أعتقد أنك تفكر في...**\n\n"
                f"**الشخصية: {guess['name']}**\n"
                f"**الوصف:** {guess['description']}\n\n"
                f"**هل كان تخميني صحيحًا؟**"
            )
            
            # إرسال الصورة إذا كانت متوفرة
            try:
                await event.client.send_file(
                    event.chat_id,
                    file=guess['absolute_picture_path'],
                    caption=result_text
                )
                await event.delete()
            except Exception:
                await event.edit(result_text)

            del ACTIVE_AKI_GAMES[game_key]
            return

        # عرض السؤال التالي
        buttons = build_aki_buttons(chat_id, user_id)
        await event.edit(f"**🧞‍♂️ | المارد يسأل (التقدم: {int(aki.progression)}%):**\n\n**- {q}**", buttons=buttons)

    except akinator.exceptions.AkiTimedOut:
        del ACTIVE_AKI_GAMES[game_key]
        await event.edit("**انتهى وقت الجلسة مع المارد. حاول بدء لعبة جديدة.**")
    except Exception as e:
        await event.edit(f"**عذرًا، حدث خطأ:**\n`{e}`")
        if game_key in ACTIVE_AKI_GAMES:
            del ACTIVE_AKI_GAMES[game_key]