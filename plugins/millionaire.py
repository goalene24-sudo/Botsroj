import asyncio
import random
from telethon import events, Button
from bot import client
# --- (مُعدَّل) تم حذف استيرادات غير ضرورية ---
from .utils import check_activation, add_points
from .millionaire_data import QUESTIONS

# --- إعدادات اللعبة ---
ACTIVE_GAMES = {} # المفتاح الآن هو (chat_id, user_id)
PRIZE_LADDER = [
    0, 100, 200, 300, 500, 1000,    # Level 1-5
    2000, 4000, 8000, 16000, 32000, # Level 6-10
    64000, 125000, 250000, 500000, 1000000 # Level 11-15
]
SAFE_POINTS = [1000, 32000]

# --- دوال مساعدة ---
def get_question_by_level(level):
    """يجلب سؤالاً عشوائياً للمستوى المطلوب."""
    eligible_questions = [q for q in QUESTIONS if q['level'] == level]
    return random.choice(eligible_questions) if eligible_questions else None

def build_keyboard(game_state):
    """ينشئ الأزرار بناءً على حالة اللعبة الحالية."""
    question_data = game_state['question_data']
    options = question_data['options']
    
    buttons = []
    row = []
    for i, option in enumerate(options):
        if option:
            callback_data = f"mil:ans:{i}:{game_state['player_id']}"
            row.append(Button.inline(option, data=callback_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    lifelines = game_state['lifelines']
    player_id = game_state['player_id']
    lifeline_buttons = [
        Button.inline("📞" if lifelines['phone'] else "❌", data=f"mil:life:phone:{player_id}"),
        Button.inline("👥" if lifelines['audience'] else "❌", data=f"mil:life:audience:{player_id}"),
        Button.inline("50:50" if lifelines['5050'] else "❌", data=f"mil:life:5050:{player_id}")
    ]
    buttons.append(lifeline_buttons)
    
    buttons.append([Button.inline("💰 انسحاب", data=f"mil:walkaway:{player_id}")])
    return buttons

async def start_game(event):
    """دالة بدء اللعبة (تم تحديثها)."""
    chat_id = event.chat_id
    player = await event.get_sender()
    player_id = player.id
    game_key = (chat_id, player_id)

    if game_key in ACTIVE_GAMES:
        return await event.reply("**لديك لعبة 'من سيربح المليون' نشطة بالفعل! أكملها أولاً أو انسحب منها.**")

    game_state = {
        "player_id": player_id,
        "player_name": player.first_name,
        "level": 1,
        "lifelines": {"5050": True, "audience": True, "phone": True},
        "message_id": None,
        "used_questions": []
    }
    
    question_data = get_question_by_level(1)
    if not question_data:
        return await event.reply("**عذراً، حدث خطأ في تحميل بنك الأسئلة.**")
        
    game_state['question_data'] = question_data
    game_state['used_questions'].append(question_data['question'])
    ACTIVE_GAMES[game_key] = game_state

    keyboard = build_keyboard(game_state)
    prize = PRIZE_LADDER[game_state['level']]
    
    msg = await event.reply(
        f"**مليونير العرب يقدم...**\n\n"
        f"**المتسابق:** [{player.first_name}](tg://user?id={player.id})\n"
        f"**السؤال رقم {game_state['level']} (على {prize} نقطة):**\n\n"
        f"**{question_data['question']}**",
        buttons=keyboard
    )
    game_state['message_id'] = msg.id


@client.on(events.CallbackQuery(pattern=b"mil:"))
async def millionaire_callback_handler(event):
    chat_id = event.chat_id
    user_id = event.sender_id
    data = event.data.decode().split(':')
    action = data[1]
    
    try:
        target_player_id = int(data[-1])
    except (ValueError, IndexError):
        return await event.answer("حدث خطأ في بيانات الزر.", alert=True)

    game_key = (chat_id, target_player_id)
    
    if user_id != target_player_id:
        return await event.answer("هذه اللعبه لا تخصك لا تحشر خشمك تريد تلعب اكتب من سيربح المليون وشوفنه شطارتك", alert=True)

    if game_key not in ACTIVE_GAMES:
        return await event.answer("هذه اللعبة قد انتهت أو لم تعد صالحة.", alert=True)

    game_state = ACTIVE_GAMES[game_key]

    if action == "ans":
        choice_index = int(data[2])
        question_data = game_state['question_data']
        correct_answer = question_data['correct']
        chosen_answer = question_data['options'][choice_index]

        if chosen_answer == correct_answer:
            await event.answer("إجابة صحيحة!", alert=False)
            current_prize = PRIZE_LADDER[game_state['level']]

            if game_state['level'] == 15:
                await add_points(chat_id, user_id, 1000000)
                await event.edit(f"**🎉🎉 مليوووون مبروووك! 🎉🎉**\n\n**لقد فزت بمليون نقطة يا [{game_state['player_name']}](tg://user?id={user_id})! أنت البطل!**")
                del ACTIVE_GAMES[game_key]
                return

            game_state['level'] += 1
            new_question = get_question_by_level(game_state['level'])
            if not new_question:
                await event.edit("**عذراً، انتهت الأسئلة! مبروك فزت بالرصيد الحالي.**")
                await add_points(chat_id, user_id, current_prize)
                del ACTIVE_GAMES[game_key]
                return

            game_state['question_data'] = new_question
            keyboard = build_keyboard(game_state)
            new_prize = PRIZE_LADDER[game_state['level']]

            await event.edit(
                f"**إجابة صحيحة! ننتقل للسؤال التالي.**\n\n"
                f"**رصيدك الحالي:** `{current_prize}` نقطة.\n"
                f"**السؤال رقم {game_state['level']} (على {new_prize} نقطة):**\n\n"
                f"**{new_question['question']}**",
                buttons=keyboard
            )
        else:
            final_prize = 0
            for sp in SAFE_POINTS:
                if PRIZE_LADDER[game_state['level']-1] >= sp:
                    final_prize = sp
            
            if final_prize > 0:
                await add_points(chat_id, user_id, final_prize)
            
            await event.edit(
                f"**للأسف إجابة خاطئة! 😔**\n\n"
                f"**الإجابة الصحيحة كانت:** `{correct_answer}`\n"
                f"**لقد فزت بـ `{final_prize}` نقطة من الرصيد المضمون.**\n\n"
                f"**شكراً لمشاركتك يا بطل!**"
            )
            del ACTIVE_GAMES[game_key]

    elif action == "life":
        life_type = data[2]
        if not game_state['lifelines'][life_type]:
            return await event.answer("لقد استخدمت وسيلة المساعدة هذه بالفعل.", alert=True)

        game_state['lifelines'][life_type] = False
        
        if life_type == '5050':
            q = game_state['question_data']
            correct = q['correct']
            incorrect_options = [opt for opt in q['options'] if opt != correct]
            to_remove = random.sample(incorrect_options, 2)
            
            new_options = [opt if opt not in to_remove else None for opt in q['options']]
            game_state['question_data']['options'] = new_options
            
            await event.answer("تم حذف إجابتين.", alert=False)

        elif life_type == 'audience':
            q = game_state['question_data']
            options = q['options']
            correct = q['correct']
            
            percs = [random.randint(5, 20) for _ in range(len(options))]
            try:
                correct_index = options.index(correct)
                percs[correct_index] = random.randint(50, 80)
            except (ValueError, IndexError):
                pass
            
            total = sum(percs)
            percs = [int((p / total) * 100) for p in percs]
            
            result_text = "**📊 نتيجة تصويت الجمهور:**\n"
            for i, opt in enumerate(options):
                if opt: result_text += f"- {opt}: {percs[i]}%\n"
            await event.answer(result_text, alert=True)

        elif life_type == 'phone':
            q = game_state['question_data']
            options = [o for o in q['options'] if o is not None]
            correct = q['correct']
            
            if random.random() < 0.80 and correct in options:
                friend_choice = correct
            else:
                friend_choice = random.choice(options)
            await event.answer(f"📞 صديقك يعتقد أن الإجابة هي: {friend_choice}", alert=True)

        keyboard = build_keyboard(game_state)
        await event.edit(buttons=keyboard)

    elif action == "walkaway":
        prize = PRIZE_LADDER[game_state['level']-1]
        if prize > 0:
            await add_points(chat_id, user_id, prize)
        
        await event.edit(
            f"**قرار حكيم! 💰**\n\n"
            f"**لقد قررت الانسحاب وفزت بـ `{prize}` نقطة!**\n\n"
            f"**مبروك!**"
        )
        del ACTIVE_GAMES[game_key]
