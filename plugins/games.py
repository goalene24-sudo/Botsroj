# plugins/games.py
import random
import asyncio
import time
from datetime import timedelta
from telethon import events, Button
from bot import client
from .utils import check_activation, add_points, RPS_GAMES, XO_GAMES, build_xo_keyboard, check_xo_winner, is_admin, db, save_db, is_command_enabled
from .quiz_data import QUIZ_QUESTIONS
from .millionaire import start_game as start_millionaire_game

# --- متغيرات خاصة بالألعاب ---
MAHIBES_GAMES = {}
CURRENT_QUIZZES = {}
LUCK_BOX_MESSAGES = [
    "فتحت الصندوق و لگيت بي ورقة مكتوب عليها 'حاول مرة أخرى'... بس الخط حلو!",
    "الصندوق طلع فارغ، بس بي ريحة دولمة. بالعافية عاللي أكلها قبلك.",
    "مبروك! لگيت بالصندوق دعاء الوالدة، وهذا أحسن من كل الكنوز.",
]

@client.on(events.NewMessage(pattern="^صندوق الحظ$"))
async def luck_box_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "صندوق الحظ" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    
    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    chat_id, user_id = event.chat_id, event.sender_id
    chat_id_str, user_id_str = str(chat_id), str(user_id)
    COOLDOWN = 10 * 60 * 60
    current_time = int(time.time())
    last_claim = db.get(chat_id_str, {}).get("luck_box", {}).get(user_id_str, 0)

    if current_time - last_claim < COOLDOWN:
        remaining_seconds = COOLDOWN - (current_time - last_claim)
        remaining_time_str = str(timedelta(seconds=int(remaining_seconds))).split('.')[0]
        return await event.reply(f"**يمعود على كيفك ويانة! صبرك شوية...\nصندوقك الجاي يفتح بعد: {remaining_time_str} ⏳**")

    opening_msg = await event.reply("**جاي نفتح الصندوق... يا ترى شنو حظك اليوم؟ 🤔🎁**")
    await asyncio.sleep(2)

    if "luck_box" not in db.get(chat_id_str, {}): db[chat_id_str]["luck_box"] = {}
    db[chat_id_str]["luck_box"][user_id_str] = current_time
    save_db(db)

    rewards = ["points", "message", "nothing"]
    probabilities = [0.60, 0.25, 0.15]
    chosen_reward = random.choices(rewards, probabilities)[0]

    if chosen_reward == "points":
        points = random.randint(10, 75)
        add_points(chat_id, user_id, points)
        await opening_msg.edit(f"**يا سلام! 🤩 فتحت الصندوق وربحت {points} نقطة! حظك نار اليوم 🔥**")
    elif chosen_reward == "message":
        message = random.choice(LUCK_BOX_MESSAGES)
        await opening_msg.edit(f"**فتحت الصندوق و... 🤔\n\n{message}**")
    else:
        await opening_msg.edit("**للأسف الصندوق طلع فارغ هل مرة 😥... حظ أوفر في المرة القادمة!**")

@client.on(events.NewMessage(pattern="^حظي$"))
async def slot_machine_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "حظي" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---

    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    emojis = ["🍓", "🍉", "🍇", "🍌", "🍋", "🍒", "🏆"]
    a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    slot_msg = await event.reply("**جاري سحب الحظ... 🎰**")
    await asyncio.sleep(1); await slot_msg.edit(f"**[ {a} | ❓ | ❓ ]**")
    await asyncio.sleep(1); await slot_msg.edit(f"**[ {a} | {b} | ❓ ]**")
    await asyncio.sleep(1)
    if a == b == c:
        points_to_win = 500 if a == "🏆" else 100
        add_points(event.chat_id, event.sender_id, points_to_win)
        result_text = f"**[ {a} | {b} | {c} ]**\n\n**مبروووووك! 🥳 حظك گعد وربحت {points_to_win} نقطة! 🎉**"
    else:
        result_text = f"**[ {a} | {b} | {c} ]**\n\n**حظ أوفر المرة الجاية... جرب مرة لخ بلكي تضبط! 😂**"
    await slot_msg.edit(result_text)

@client.on(events.NewMessage(pattern="^xo$"))
async def xo_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "xo" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---

    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**يمعود رپلَي على واحد حتى تلعبون!**")
    player1, player2 = await event.get_sender(), await reply.get_sender()
    if player1.id == player2.id: return await event.reply("**تلعب ويه نفسك؟ شنو فلمك؟ 😐**")
    if player2.bot: return await event.reply("**البوتات متلعب XO.**")
    game = {'board': ['-'] * 9, 'player_x': player1.id, 'player_o': player2.id, 'turn': player1.id, 'symbol': 'X', 'p1_name': player1.first_name, 'p2_name': player2.first_name}
    board_buttons = build_xo_keyboard(game['board'])
    game_msg = await event.reply(f"**⚔️ لعبة XO بدأت!**\n\n**- اللاعب 𝚇:** [{player1.first_name}](tg://user?id={player1.id})\n**- اللاعب 𝙾:** [{player2.first_name}](tg://user?id={player2.id})\n\n**سره {player1.first_name} (𝚇)**", buttons=board_buttons)
    XO_GAMES[game_msg.id] = game

@client.on(events.NewMessage(pattern="^حجره ورقه مقص$"))
async def rps_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "حجره ورقه مقص" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---

    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**رپلَي على واحد حتى تتحده!**")
    player1, player2 = await event.get_sender(), await reply.get_sender()
    if player1.id == player2.id: return await event.reply("**شنو تتحده نفسك؟**")
    if player2.bot: return await event.reply("**البوتات متلعب هاي السوالف.**")
    buttons = [[Button.inline("🗿 حجرة", data=f"rps:rock:{player1.id}:{player2.id}"), Button.inline("📄 ورقة", data=f"rps:paper:{player1.id}:{player2.id}"), Button.inline("✂️ مقص", data=f"rps:scissors:{player1.id}:{player2.id}")]]
    challenge_msg = await event.reply(f"**⚔️ تحدي!**\n\n**[{player1.first_name}](tg://user?id={player1.id}) يتحدى [{player2.first_name}](tg://user?id={player2.id})!**\n\n**يلا كل واحد بيكم يختار...**", buttons=buttons)
    RPS_GAMES[challenge_msg.id] = {"p1": player1.id, "p2": player2.id, "p1_choice": None, "p2_choice": None, "p1_name": player1.first_name, "p2_name": player2.first_name}

@client.on(events.NewMessage(pattern="^كويز$"))
async def start_quiz_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "كويز" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---

    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    question_data = random.choice(QUIZ_QUESTIONS)
    question, options, correct_answer = question_data["question"], question_data["options"].copy(), question_data["answer"]
    random.shuffle(options)
    buttons = [Button.inline(opt, data=f"quiz:{opt}:{correct_answer}") for opt in options]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    await event.reply(f"**يابه سؤال عالطاير 🚁... جاوب صح وشوفنا شطارتك:\n\n{question}**", buttons=keyboard)

@client.on(events.NewMessage(pattern="^محيبس$"))
async def start_mahbis_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "محيبس" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---

    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    chat_id = event.chat_id
    if chat_id in MAHIBES_GAMES:
        return await event.reply("**اكو لعبة محيبس بعدها شغالة!**")

    player = await event.get_sender()
    winner_pos = random.randint(0, 4)
    MAHIBES_GAMES[chat_id] = {
        "player_id": player.id,
        "winner_pos": winner_pos
    }

    buttons = [Button.inline("✊", data=f"mahbis:guess:{i}") for i in range(5)]
    keyboard = [buttons]

    await event.reply(
        f"**💎 لعبة المحيبس!**\n\n**يا [{player.first_name}](tg://user?id={player.id})، المحيبس ضايع بوحدة من هاي الأيادي... وين تتوقع؟**",
        buttons=keyboard
    )

    await asyncio.sleep(30)
    if chat_id in MAHIBES_GAMES and MAHIBES_GAMES[chat_id]["winner_pos"] == winner_pos:
        del MAHIBES_GAMES[chat_id]
        await event.respond("**انتهى الوقت! ⏰ محد لزم المحيبس.**")

@client.on(events.NewMessage(pattern="^من سيربح المليون$"))
async def millionaire_start_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "من سيربح المليون" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---

    if not is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    await start_millionaire_game(event)
