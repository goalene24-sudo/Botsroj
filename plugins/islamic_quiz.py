import logging
import random
from telethon import events, Button

from bot import client
# --- استيراد مكونات قاعدة البيانات ---
from database import AsyncDBSession
from models import User

# --- استيراد الدوال المساعدة والبيانات ---
from .utils import check_activation, get_or_create_user, add_points
from .islamic_quiz_data import ISLAMIC_QUESTIONS

logger = logging.getLogger(__name__)

# قاموس لتخزين الكويزات النشطة حالياً
CURRENT_ISLAMIC_QUIZZES = {}

@client.on(events.NewMessage(pattern=r"^[!/](كويز اسلامي|كويز ديني)$"))
async def islamic_quiz_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    try:
        # اختيار سؤال عشوائي من بنك الأسئلة
        quiz = random.choice(ISLAMIC_QUESTIONS)
        question = quiz["question"]
        correct_answer = quiz["answer"]
        options = quiz["options"]
        
        # خلط الخيارات لضمان عدم ظهورها بنفس الترتيب
        random.shuffle(options)
        
        # بناء الأزرار
        buttons = []
        for option in options:
            # نستخدم "1" للإجابة الصحيحة و "0" للخاطئة
            is_correct = "1" if option == correct_answer else "0"
            buttons.append(Button.inline(option, data=f"islamic_quiz:{is_correct}"))
        
        # تقسيم الأزرار إلى صفوف (كل صف فيه زرين)
        keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

        quiz_message = (
            "🕌 | **اختبر معلوماتك الدينية**\n\n"
            f"**السؤال:** {question}"
        )

        sent_message = await event.reply(quiz_message, buttons=keyboard)

        # تخزين معلومات الكويز للتحقق منها لاحقاً
        CURRENT_ISLAMIC_QUIZZES[sent_message.id] = {
            "correct_answer": correct_answer,
            "participants": set() # لتتبع من حاول الإجابة
        }

    except Exception as e:
        logger.error(f"Error in islamic_quiz_handler: {e}", exc_info=True)
        await event.reply("**حدث خطأ أثناء إنشاء الكويز.**")

@client.on(events.CallbackQuery(pattern=b"^islamic_quiz:"))
async def islamic_quiz_callback_handler(event):
    result = event.data.decode().split(":")[1]
    msg_id = event.message_id
    user_id = event.sender_id

    if msg_id not in CURRENT_ISLAMIC_QUIZZES:
        return await event.answer("انتهى وقت هذا الكويز أو تم الإجابة عليه بالفعل.", alert=True)

    quiz_info = CURRENT_ISLAMIC_QUIZZES[msg_id]
    if user_id in quiz_info["participants"]:
        return await event.answer("لقد قمت بالمحاولة بالفعل!", alert=True)

    quiz_info["participants"].add(user_id)
    
    user_entity = await event.get_sender()
    original_message = await event.get_message()
    question_text = original_message.text
    correct_answer_text = quiz_info['correct_answer']

    if result == "1":
        points_to_win = random.randint(10, 20)
        await add_points(event.chat_id, user_id, points_to_win)
        
        reply_text = (
            f"{question_text}\n\n"
            f"**🏆 إجابة صحيحة!**\n"
            f"**الفائز هو [{user_entity.first_name}](tg://user?id={user_id}) وقد ربح {points_to_win} نقطة!**\n"
            f"**الإجابة كانت بالفعل: {correct_answer_text}**"
        )
        await event.edit(reply_text, buttons=None)
        del CURRENT_ISLAMIC_QUIZZES[msg_id] # حذف الكويز بعد الإجابة الصحيحة
    else:
        await event.answer(f"للاسف إجابتك خاطئة يا {user_entity.first_name}! 😥", alert=True)