# plugins/millionaire.py
import asyncio
import random
from telethon import events, Button
from bot import client
from .utils import check_activation, add_points, db, save_db
from .millionaire_data import QUESTIONS

# --- إعدادات اللعبة ---
ACTIVE_GAMES = {}
PRIZE_LADDER = [
    0, 100, 200, 300, 500, 1000,  # Level 1-5
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
    
    # بناء أزرار الخيارات
    buttons = []
    row = []
    for i, option in enumerate(options):
        if option: # تحقق مما إذا كان الخيار موجوداً (لم يتم حذفه بـ 50:50)
            row.append(Button.inline(option, data=f"mil:ans:{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # بناء أزرار وسائل المساعدة
    lifelines = game_state['lifelines']
    lifeline_buttons = [
        Button.inline("📞" if lifelines['phone'] else "❌", data="mil:life:phone"),
        Button.inline("👥" if lifelines['audience'] else "❌", data="mil:life:audience"),
        Button.inline("50:50" if lifelines['5050'] else "❌", data="mil:life:5050")
    ]
    buttons.append(lifeline_buttons)
    
    # زر الانسحاب
    buttons.append([Button.inline("💰 انسحاب", data="mil:walkaway")])
    return buttons

async def start_game(event):
    """دالة بدء اللعبة."""
    chat_id = event.chat_id
    player = await event.get_sender()

    if chat_id in ACTIVE_GAMES:
        return await event.reply("**هناك لعبة 'من سيربح المليون' تعمل بالفعل في هذه المجموعة!**")

    # تهيئة حالة اللعبة الجديدة
    game_state = {
        "player_id": player.id,
        "player_name": player.first_name,
        "level": 1,
        "lifelines": {"5050": True, "audience": True, "phone": True},
        "message_id": None
    }
    
    question_data = get_question_by_level(1)
    if not question_data:
        return await event.reply("**عذراً، حدث خطأ في تحميل بنك الأسئلة.**")
        
    game_state['question_data'] = question_data
    ACTIVE_GAMES[chat_id] = game_state

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

    if chat_id not in ACTIVE_GAMES:
        return await event.answer("هذه اللعبة قد انتهت.", alert=True)

    game_state = ACTIVE_GAMES[chat_id]
    if user_id != game_state['player_id']:
        return await event.answer("هذه اللعبة ليست لك!", alert=True)

    data = event.data.decode().split(':')
    action = data[1]

    if action == "ans":
        # ... معالجة الإجابة ...
        choice_index = int(data[2])
        question_data = game_state['question_data']
        correct_answer = question_data['correct']
        chosen_answer = question_data['options'][choice_index]

        if chosen_answer == correct_answer:
            await event.answer("إجابة صحيحة!", alert=False)
            current_prize = PRIZE_LADDER[game_state['level']]

            if game_state['level'] == 15:
                # الفوز بالمليون
                add_points(chat_id, user_id, 1000000)
                await event.edit(f"**🎉🎉 مليوووون مبروووك! 🎉🎉**\n\n**لقد فزت بمليون نقطة! أنت البطل!**")
                del ACTIVE_GAMES[chat_id]
                return

            game_state['level'] += 1
            new_question = get_question_by_level(game_state['level'])
            if not new_question:
                await event.edit("**عذراً، انتهت الأسئلة! مبروك فزت بالرصيد الحالي.**")
                add_points(chat_id, user_id, current_prize)
                del ACTIVE_GAMES[chat_id]
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
            # إجابة خاطئة
            final_prize = 0
            for sp in SAFE_POINTS:
                if PRIZE_LADDER[game_state['level']-1] >= sp:
                    final_prize = sp
            
            if final_prize > 0:
                add_points(chat_id, user_id, final_prize)
            
            await event.edit(
                f"**للأسف إجابة خاطئة! 😔**\n\n"
                f"**الإجابة الصحيحة كانت:** `{correct_answer}`\n"
                f"**لقد فزت بـ `{final_prize}` نقطة من الرصيد المضمون.**\n\n"
                f"**شكراً لمشاركتك!**"
            )
            del ACTIVE_GAMES[chat_id]

    elif action == "life":
        # ... معالجة وسائل المساعدة ...
        life_type = data[2]
        if not game_state['lifelines'][life_type]:
            return await event.answer("لقد استخدمت وسيلة المساعدة هذه بالفعل.", alert=True)

        game_state['lifelines'][life_type] = False
        
        if life_type == '5050':
            q = game_state['question_data']
            correct = q['correct']
            incorrect_options = [opt for opt in q['options'] if opt != correct]
            to_remove = random.sample(incorrect_options, 2)
            
            new_options = []
            for opt in q['options']:
                new_options.append(opt if opt not in to_remove else None)
            game_state['question_data']['options'] = new_options
            
            await event.answer("تم حذف إجابتين.", alert=False)

        elif life_type == 'audience':
            q = game_state['question_data']
            options = q['options']
            correct = q['correct']
            
            percs = [random.randint(5, 20) for _ in range(len(options))]
            correct_index = options.index(correct)
            percs[correct_index] = random.randint(50, 80)
            
            total = sum(percs)
            percs = [int((p / total) * 100) for p in percs]
            
            result_text = "**📊 نتيجة تصويت الجمهور:**\n"
            for i, opt in enumerate(options):
                if opt: result_text += f"- {opt}: {percs[i]}%\n"
            await event.answer(result_text, alert=True)

        elif life_type == 'phone':
            q = game_state['question_data']
            options = q['options']
            correct = q['correct']
            
            # الصديق ذكي، 80% يقول الإجابة الصحيحة
            if random.random() < 0.80:
                friend_choice = correct
            else:
                friend_choice = random.choice([o for o in options if o is not None])
            await event.answer(f"📞 صديقك يعتقد أن الإجابة هي: {friend_choice}", alert=True)

        keyboard = build_keyboard(game_state)
        await event.edit(buttons=keyboard)

    elif action == "walkaway":
        # ... معالجة الانسحاب ...
        prize = PRIZE_LADDER[game_state['level']-1]
        if prize > 0:
            add_points(chat_id, user_id, prize)
        
        await event.edit(
            f"**قرار حكيم! 💰**\n\n"
            f"**لقد قررت الانسحاب وفزت بـ `{prize}` نقطة!**\n\n"
            f"**مبروك!**"
        )
        del ACTIVE_GAMES[chat_id]