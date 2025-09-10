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
            Button.inline("✅ Yes", data=f"aki_ans:{chat_id}:{user_id}:y"),
            Button.inline("❌ No", data=f"aki_ans:{chat_id}:{user_id}:n"),
            Button.inline("❓ I don't know", data=f"aki_ans:{chat_id}:{user_id}:i"),
        ],
        [
            Button.inline("👍 Probably", data=f"aki_ans:{chat_id}:{user_id}:p"),
            Button.inline("👎 Probably not", data=f"aki_ans:{chat_id}:{user_id}:pn"),
        ],
        [
            Button.inline("🔙 Back", data=f"aki_ans:{chat_id}:{user_id}:b"),
        ],
        [
            Button.inline("🚫 End Game", data=f"aki_ans:{chat_id}:{user_id}:end"),
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
        # --- (تم التعديل) إزالة تحديد اللغة من هنا ليتوافق مع المكتبة ---
        q = await aki.start_game(child_mode=True)
        
        game_state = {
            "aki": aki,
            "question": q,
            "message_id": None,
        }
        
        buttons = build_aki_buttons(chat_id, user_id)
        # تم تغيير النص ليناسب اللغة الإنجليزية المؤقتة
        msg = await zed.edit(f"**🧞‍♂️ | Akinator asks:**\n\n**- {q}**", buttons=buttons)
        
        game_state["message_id"] = msg.id
        ACTIVE_AKI_GAMES[game_key] = game_state

    except Exception as e:
        await zed.edit(f"**عذرًا، حدث خطأ أثناء بدء اللعبة:**\n`{e}`")


@client.on(events.CallbackQuery(pattern=b"aki_ans:(.*)"))
async def handle_akinator_answer(event):
    data_str = event.data.decode('utf-8')
    _, chat_id_str, user_id_str, answer_code = data_str.split(':')
    
    chat_id = int(chat_id_str)
    user_id = int(user_id_str)

    if event.sender_id != user_id:
        await event.answer("🚫 | This game is not for you!", alert=True)
        return

    game_key = (chat_id, user_id)

    if game_key not in ACTIVE_AKI_GAMES:
        await event.answer("This game has ended or been deleted.", alert=True)
        await event.edit("`This game has ended.`")
        return
        
    game_state = ACTIVE_AKI_GAMES[game_key]
    aki = game_state["aki"]
    
    # تحويل الرموز إلى الإجابات النصية التي تفهمها المكتبة
    answer_map = {
        'y': 'yes', 'n': 'no', 'i': "i don't know",
        'p': 'probably', 'pn': 'probably not', 'b': 'back'
    }
    answer_text = answer_map.get(answer_code)

    if answer_code == "end":
        del ACTIVE_AKI_GAMES[game_key]
        await event.edit("**🧞‍♂️ | The game was ended at your request.**")
        return
        
    await event.edit("`Analyzing your answer...`")
    
    try:
        if answer_text == "back":
            q = await aki.back()
        else:
            q = await aki.answer(answer_text)

        if aki.progression >= 80:
            await aki.win()
            guess = aki.first_guess
            
            result_text = (
                f"**🧞‍♂️ | I think you are thinking of...**\n\n"
                f"**Character: {guess['name']}**\n"
                f"**Description:** {guess['description']}\n\n"
                f"**Was my guess correct?**"
            )
            
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

        buttons = build_aki_buttons(chat_id, user_id)
        await event.edit(f"**🧞‍♂️ | Akinator asks (Progress: {int(aki.progression)}%):**\n\n**- {q}**", buttons=buttons)

    except akinator.exceptions.AkiTimedOut:
        del ACTIVE_AKI_GAMES[game_key]
        await event.edit("**Session with the genie has timed out. Try starting a new game.**")
    except Exception as e:
        await event.edit(f"**Sorry, an error occurred:**\n`{e}`")
        if game_key in ACTIVE_AKI_GAMES:
            del ACTIVE_AKI_GAMES[game_key]
