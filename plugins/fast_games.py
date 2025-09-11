import random
import asyncio
from telethon import events

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from database import DBSession
from models import GlobalSetting
import json

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, add_points
from .game_data import DIFFERENCE_SETS, FLAG_QUIZ, CAPITAL_QUIZ, OPPOSITES, PROVERBS

# --- متغيرات خاصة بالألعاب السريعة (لا تحتاج قاعدة بيانات) ---
DIFFERENCE_GAMES, FLAG_QUIZ_GAMES, CAPITAL_QUIZ_GAMES = {}, {}, {}
MATH_GAMES, OPPOSITES_GAMES, PROVERBS_GAMES = {}, {}, {}
SMILEY_GAMES = {}
SMILEY_LIST = ["😀", "😂", "🥰", "🤔", "😎", "👍", "🔥", "🚀", "💡", "🎲", "❤️", "⭐", "⚠️", "👑", "🍕", "⚽", "🇮🇶", "😇", "☠️", "👀"]
CURRENT_GUESSES, UNSCRAMBLE_GAMES = {}, {}
WORDS_LIST = [
    "بغداد", "بصرة", "عراق", "سيارة", "مدرسة", "مستشفى", "برتقال", "تفاح", "كهرباء",
    "انترنت", "تلفزيون", "شاحنة", "طائرة", "دجلة", "فرات", "بايسكل", "منديل", "جسر",
]

# --- دالة مساعدة للتحقق من الأوامر المعطلة عالميًا ---
async def is_globally_disabled(command_name):
    """التحقق إذا كان الأمر معطلاً على مستوى البوت."""
    async with DBSession() as session:
        result = await session.execute(
            select(GlobalSetting).where(GlobalSetting.key == "disabled_cmds")
        )
        setting = result.scalar_one_or_none()
        if setting and setting.value:
            disabled_list = json.loads(setting.value)
            return command_name in disabled_list
        return False

def scramble_word(word):
    word_list = list(word)
    random.shuffle(word_list)
    return "".join(word_list)

@client.on(events.NewMessage(pattern="^فككها$"))
async def start_unscramble_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("فككها"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    
    chat_id = event.chat_id
    if chat_id in UNSCRAMBLE_GAMES:
        return await event.reply("**اكو لعبة بعدها شغالة! كملوها بالاول حتى نبدي وحدة جديدة.**")
    
    word = random.choice(WORDS_LIST)
    scrambled = scramble_word(word)
    while scrambled == word:
        scrambled = scramble_word(word)
        
    UNSCRAMBLE_GAMES[chat_id] = word
    await event.reply(f"**🤔 لعبة فككها!**\n\n**الكلمة المبعثرة هي:** `{scrambled}`\n\n**تلميح: الكلمة مكونة من {len(word)} حروف. منو الذيب اللي يعرفها؟ عدكم دقيقة وحده!**")
    
    await asyncio.sleep(60)
    
    if chat_id in UNSCRAMBLE_GAMES and UNSCRAMBLE_GAMES.get(chat_id) == word:
        del UNSCRAMBLE_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ محد عرف يحلها للأسف.**\n\n**الكلمة الصحيحة جانت {word}.**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in UNSCRAMBLE_GAMES and not e.text.startswith('/')))
async def check_unscramble_handler(event):
    chat_id = event.chat_id
    correct_word = UNSCRAMBLE_GAMES.get(chat_id)

    if event.text.strip() == correct_word:
        winner = await event.get_sender()
        del UNSCRAMBLE_GAMES[chat_id]
        await add_points(chat_id, winner.id, 25)
        await event.reply(f"**โห! عاشت ايدك يا بطل [{winner.first_name}](tg://user?id={winner.id})! 🏆**\n\n**جوابك صح، الكلمة هي {correct_word}. ربحت 25 نقطة!**")

@client.on(events.NewMessage(pattern="^تخمين$"))
async def start_guessing_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("تخمين"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    
    GUESS_ITEMS = {"برج إيفل": "أنا معلم مشهور كلش بباريس. منو آني؟ 🗼", "الكهرباء": "آني شي محد يكدر يشوفني، بس الكل يحتاجني. منو آني؟ 💡"}
    correct_answer, hint = random.choice(list(GUESS_ITEMS.items()))
    await event.reply(f"**يلا نلعب تخمين! 🤔 شغل عقلك وحاول تعرف الجواب:\n\n{hint}**\n\n**اللي يعرف الجواب يدزه برسالة 👇**")
    CURRENT_GUESSES[event.chat_id] = {"answer": correct_answer}

@client.on(events.NewMessage(func=lambda e: e.chat_id in CURRENT_GUESSES and not e.text.startswith('/')))
async def guess_reply_handler(event):
    chat_id = event.chat_id
    correct_answer = CURRENT_GUESSES.get(chat_id, {}).get("answer")
    if not correct_answer: return
    user_guess = event.raw_text
    if user_guess.strip() == correct_answer:
        winner = await event.get_sender()
        await event.reply(f"**عاششششت ايدك [{winner.first_name}](tg://user?id={winner.id})! 🧠 جبتها والله! الجواب هو '{correct_answer}'.**")
        await add_points(chat_id, winner.id, 10)
        del CURRENT_GUESSES[chat_id]

@client.on(events.NewMessage(pattern="^سمايلات|سمايل$"))
async def start_smiley_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    command_name = "سمايلات" if event.raw_text.lower().startswith("سمايلات") else "سمايل"
    if await is_globally_disabled(command_name):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")

    chat_id = event.chat_id
    if chat_id in SMILEY_GAMES:
        return await event.reply("**اكو لعبة سمايلات بعدها شغالة، لتستعجل!**")
    
    chosen_smiley = random.choice(SMILEY_LIST)
    SMILEY_GAMES[chat_id] = {"smiley": chosen_smiley}
    
    await event.reply(f"**لعبة السمايلات بدأت!**\n\n**اسرع واحد يدز هذا السمايل يفوز:**\n\n`{chosen_smiley}`")
    
    await asyncio.sleep(15)
    
    if chat_id in SMILEY_GAMES and SMILEY_GAMES[chat_id]["smiley"] == chosen_smiley:
        del SMILEY_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰**\n\n**للاسف محد لحگ يدز السمايل الصحيح اللي هو:** {chosen_smiley}")

@client.on(events.NewMessage(func=lambda e: e.chat_id in SMILEY_GAMES and not (e.sender and e.sender.bot)))
async def check_smiley_handler(event):
    chat_id = event.chat_id
    if chat_id not in SMILEY_GAMES: return
    correct_smiley = SMILEY_GAMES[chat_id]["smiley"]
    
    if event.text.strip() == correct_smiley:
        winner = await event.get_sender()
        del SMILEY_GAMES[chat_id]
        await add_points(chat_id, winner.id, 15)
        await event.reply(f"**كفووو عليك [{winner.first_name}](tg://user?id={winner.id})! 🏆**\n\n**أنت أسرع واحد وجبتها صح! ربحت 15 نقطة.**")

@client.on(events.NewMessage(pattern="^المختلف$"))
async def start_difference_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("المختلف"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    chat_id = event.chat_id
    if chat_id in DIFFERENCE_GAMES: return await event.reply("**اكو لعبة مختلف بعدها شغالة!**")
    game_data = random.choice(DIFFERENCE_SETS)
    DIFFERENCE_GAMES[chat_id] = {"answer": game_data["answer"]}
    await event.reply(f"**🧐 لعبة المختلف!**\n\n**طلع السمايل المختلف من بين هاي السمايلات 👇**\n\n`{game_data['set']}`")
    await asyncio.sleep(20)
    if chat_id in DIFFERENCE_GAMES and DIFFERENCE_GAMES[chat_id]["answer"] == game_data["answer"]:
        del DIFFERENCE_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ السمايل المختلف چان {game_data['answer']}**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in DIFFERENCE_GAMES))
async def check_difference_handler(event):
    chat_id = event.chat_id
    if chat_id not in DIFFERENCE_GAMES: return
    correct_answer = DIFFERENCE_GAMES[chat_id]["answer"]
    if event.text.strip() == correct_answer:
        winner = await event.get_sender()
        del DIFFERENCE_GAMES[chat_id]
        await add_points(chat_id, winner.id, 20)
        await event.reply(f"**عفية! [{winner.first_name}](tg://user?id={winner.id}) جبتها صح! ✅ ربحت 20 نقطة.**")

@client.on(events.NewMessage(pattern="^اعلام الدول$"))
async def start_flag_quiz_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("اعلام الدول"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    chat_id = event.chat_id
    if chat_id in FLAG_QUIZ_GAMES: return await event.reply("**اكو سؤال أعلام بعده فعال!**")
    flag, country = random.choice(list(FLAG_QUIZ.items()))
    FLAG_QUIZ_GAMES[chat_id] = {"answer": country}
    await event.reply(f"**🏳️‍🌈 لعبة الأعلام!**\n\n**هذا علم يا دولة؟**\n\n# {flag}")
    await asyncio.sleep(25)
    if chat_id in FLAG_QUIZ_GAMES and FLAG_QUIZ_GAMES[chat_id]["answer"] == country:
        del FLAG_QUIZ_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ الجواب الصحيح چان: {country}**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in FLAG_QUIZ_GAMES))
async def check_flag_handler(event):
    chat_id = event.chat_id
    if chat_id not in FLAG_QUIZ_GAMES: return
    correct_answer = FLAG_QUIZ_GAMES[chat_id]["answer"]
    if event.text.strip() == correct_answer:
        winner = await event.get_sender()
        del FLAG_QUIZ_GAMES[chat_id]
        await add_points(chat_id, winner.id, 20)
        await event.reply(f"**صحيح! [{winner.first_name}](tg://user?id={winner.id}) جوابك مضبوط! 👍 ربحت 20 نقطة.**")

@client.on(events.NewMessage(pattern="^عواصم الدول$"))
async def start_capital_quiz_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("عواصم الدول"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    chat_id = event.chat_id
    if chat_id in CAPITAL_QUIZ_GAMES: return await event.reply("**اكو سؤال عواصم بعده فعال!**")
    country, capital = random.choice(list(CAPITAL_QUIZ.items()))
    CAPITAL_QUIZ_GAMES[chat_id] = {"answer": capital}
    await event.reply(f"**🌍 لعبة العواصم!**\n\n**شنو عاصمة دولة '{country}'؟**")
    await asyncio.sleep(25)
    if chat_id in CAPITAL_QUIZ_GAMES and CAPITAL_QUIZ_GAMES[chat_id]["answer"] == capital:
        del CAPITAL_QUIZ_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ الجواب الصحيح چان: {capital}**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in CAPITAL_QUIZ_GAMES))
async def check_capital_handler(event):
    chat_id = event.chat_id
    if chat_id not in CAPITAL_QUIZ_GAMES: return
    correct_answer = CAPITAL_QUIZ_GAMES[chat_id]["answer"]
    if event.text.strip() == correct_answer:
        winner = await event.get_sender()
        del CAPITAL_QUIZ_GAMES[chat_id]
        await add_points(chat_id, winner.id, 20)
        await event.reply(f"**بالضبط! [{winner.first_name}](tg://user?id={winner.id}) جوابك صحيح! ✅ ربحت 20 نقطة.**")

@client.on(events.NewMessage(pattern="^رياضيات$"))
async def start_math_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("رياضيات"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    chat_id = event.chat_id
    if chat_id in MATH_GAMES: return await event.reply("**اكو سؤال رياضيات بعده فعال!**")
    num1, num2 = random.randint(10, 99), random.randint(10, 99)
    answer = num1 + num2
    MATH_GAMES[chat_id] = {"answer": str(answer)}
    await event.reply(f"**🧮 لعبة الرياضيات!**\n\n**اسرع واحد يحل هاي المسألة:**\n`{num1} + {num2} = ?`")
    await asyncio.sleep(20)
    if chat_id in MATH_GAMES and MATH_GAMES[chat_id]["answer"] == str(answer):
        del MATH_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ الجواب الصحيح چان: {answer}**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in MATH_GAMES))
async def check_math_handler(event):
    chat_id = event.chat_id
    if chat_id not in MATH_GAMES: return
    correct_answer = MATH_GAMES[chat_id]["answer"]
    if event.text.strip() == correct_answer:
        winner = await event.get_sender()
        del MATH_GAMES[chat_id]
        await add_points(chat_id, winner.id, 20)
        await event.reply(f"**ذكي! [{winner.first_name}](tg://user?id={winner.id}) جوابك صح! 🧠 ربحت 20 نقطة.**")

@client.on(events.NewMessage(pattern="^العكس$"))
async def start_opposites_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("العكس"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    chat_id = event.chat_id
    if chat_id in OPPOSITES_GAMES: return await event.reply("**اكو لعبة عكس الكلمة بعدها شغالة!**")
    word, opposite = random.choice(list(OPPOSITES.items()))
    OPPOSITES_GAMES[chat_id] = {"answer": opposite}
    await event.reply(f"**↔️ لعبة العكس!**\n\n**شنو عكس كلمة '{word}'؟**")
    await asyncio.sleep(20)
    if chat_id in OPPOSITES_GAMES and OPPOSITES_GAMES[chat_id]["answer"] == opposite:
        del OPPOSITES_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ الجواب الصحيح چان: {opposite}**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in OPPOSITES_GAMES))
async def check_opposites_handler(event):
    chat_id = event.chat_id
    if chat_id not in OPPOSITES_GAMES: return
    correct_answer = OPPOSITES_GAMES[chat_id]["answer"]
    if event.text.strip() == correct_answer:
        winner = await event.get_sender()
        del OPPOSITES_GAMES[chat_id]
        await add_points(chat_id, winner.id, 20)
        await event.reply(f"**بالضبط! [{winner.first_name}](tg://user?id={winner.id}) جوابك صحيح! 🤓 ربحت 20 نقطة.**")

@client.on(events.NewMessage(pattern="^اكمل المثل$"))
async def start_proverb_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("اكمل المثل"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")

    chat_id = event.chat_id
    if chat_id in PROVERBS_GAMES: return await event.reply("**اكو مثل بعده محد مكمله!**")
    proverb = random.choice(PROVERBS)
    PROVERBS_GAMES[chat_id] = {"answer": proverb["a"]}
    await event.reply(f"**📖 لعبة أكمل المثل!**\n\n**كمل هذا المثل العراقي:**\n_{proverb['q']}..._")
    await asyncio.sleep(30)
    if chat_id in PROVERBS_GAMES and PROVERBS_GAMES[chat_id]["answer"] == proverb["a"]:
        del PROVERBS_GAMES[chat_id]
        await event.reply(f"**انتهى الوقت! ⏰ التكملة الصحيحة چانت: {proverb['a']}**")

@client.on(events.NewMessage(func=lambda e: e.chat_id in PROVERBS_GAMES))
async def check_proverb_handler(event):
    chat_id = event.chat_id
    if chat_id not in PROVERBS_GAMES: return
    correct_answer = PROVERBS_GAMES[chat_id]["answer"]
    if event.text.strip() == correct_answer:
        winner = await event.get_sender()
        del PROVERBS_GAMES[chat_id]
        await add_points(chat_id, winner.id, 25)
        await event.reply(f"**عفية عليك حجي! [{winner.first_name}](tg://user?id={winner.id}) كملتها صح! 👨‍🦳 ربحت 25 نقطة.**")
