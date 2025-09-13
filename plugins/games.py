import random
import asyncio
import time
from datetime import datetime, timedelta
import json
from telethon import events, Button
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import GlobalSetting, User 
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, add_points, XO_GAMES, build_xo_keyboard, check_xo_winner, is_command_enabled, get_or_create_user
from .quiz_data import QUIZ_QUESTIONS
from .millionaire import start_game as start_millionaire_game
import logging

logger = logging.getLogger(__name__)

# --- متغيرات خاصة بالألعاب (لا تحتاج قاعدة بيانات) ---
MAHIBES_GAMES = {}
CURRENT_QUIZZES = {} # سيتم استخدامه الآن
RPS_GAMES = {}
LUCK_BOX_MESSAGES = [
    "فتحت الصندوق و لگيت بي ورقة مكتوب عليها 'حاول مرة أخرى'... بس الخط حلو!",
    "الصندوق طلع فارغ، بس بي ريحة دولمة. بالعافية عاللي أكلها قبلك.",
    "مبروك! لگيت بالصندوق دعاء الوالدة، وهذا أحسن من كل الكنوز.",
]

# --- (بقية الكود يبقى كما هو حتى نصل إلى دالة الكويز) ---

async def is_globally_disabled(command_name):
    async with AsyncDBSession() as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == "disabled_cmds"))
        setting = result.scalar_one_or_none()
        if setting and isinstance(setting.value, list): return command_name in setting.value
        return False

@client.on(events.NewMessage(pattern="^صندوق الحظ$"))
async def luck_box_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("صندوق الحظ"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
    chat_id, user_id, COOLDOWN, current_time = event.chat_id, event.sender_id, 10 * 60 * 60, int(time.time())
    async with AsyncDBSession() as session:
        user = await get_or_create_user(session, chat_id, user_id)
        inventory = user.inventory or {}
        last_claim = inventory.get("luck_box_claim", 0)
        if current_time - last_claim < COOLDOWN:
            remaining_seconds = COOLDOWN - (current_time - last_claim)
            remaining_time_str = str(timedelta(seconds=int(remaining_seconds))).split('.')[0]
            return await event.reply(f"**صندوقك الجاي يفتح بعد: {remaining_time_str} ⏳**")
        opening_msg = await event.reply("**جاي نفتح الصندوق... 🤔🎁**")
        await asyncio.sleep(2)
        inventory["luck_box_claim"] = current_time
        user.inventory = inventory
        flag_modified(user, "inventory")
        rewards, probabilities = ["points", "message", "nothing"], [0.60, 0.25, 0.15]
        chosen_reward = random.choices(rewards, probabilities)[0]
        if chosen_reward == "points":
            points = random.randint(10, 75)
            await add_points(chat_id, user_id, points)
            await opening_msg.edit(f"**يا سلام! 🤩 فتحت الصندوق وربحت {points} نقطة!**")
        elif chosen_reward == "message":
            await opening_msg.edit(f"**فتحت الصندوق و... 🤔\n\n{random.choice(LUCK_BOX_MESSAGES)}**")
        else:
            await opening_msg.edit("**للأسف الصندوق طلع فارغ هل مرة 😥... حظ أوفر!**")
        await session.commit()

@client.on(events.NewMessage(pattern="^حظي$"))
async def slot_machine_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("حظي"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
    emojis = ["🍓", "🍉", "🍇", "🍌", "🍋", "🍒", "🏆"]
    a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    slot_msg = await event.reply("**جاري سحب الحظ... 🎰**")
    await asyncio.sleep(1); await slot_msg.edit(f"**[ {a} | ❓ | ❓ ]**")
    await asyncio.sleep(1); await slot_msg.edit(f"**[ {a} | {b} | ❓ ]**")
    await asyncio.sleep(1)
    if a == b == c:
        points_to_win = 500 if a == "🏆" else 100
        await add_points(event.chat_id, event.sender_id, points_to_win)
        result_text = f"**[ {a} | {b} | {c} ]**\n\n**مبروووووك! 🥳 ربحت {points_to_win} نقطة!**"
    else:
        result_text = f"**[ {a} | {b} | {c} ]**\n\n**حظ أوفر المرة الجاية... 😂**"
    await slot_msg.edit(result_text)

@client.on(events.NewMessage(pattern="^xo$"))
async def xo_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("xo"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**يمعود رپلَي على واحد حتى تلعبون!**")
    player1, player2 = await event.get_sender(), await reply.get_sender()
    if player1.id == player2.id: return await event.reply("**تلعب ويه نفسك؟ 😐**")
    if player2.bot: return await event.reply("**البوتات متلعب XO.**")
    game = {'board': ['-'] * 9, 'player_x': player1.id, 'player_o': player2.id, 'turn': player1.id, 'symbol': 'X', 'p1_name': player1.first_name, 'p2_name': player2.first_name}
    board_buttons = build_xo_keyboard(game['board'])
    game_msg = await event.reply(f"**⚔️ لعبة XO بدأت!**\n\n**- اللاعب 𝚇:** [{player1.first_name}](tg://user?id={player1.id})\n**- اللاعب 𝙾:** [{player2.first_name}](tg://user?id={player2.id})\n\n**سره {player1.first_name} (𝚇)**", buttons=board_buttons)
    XO_GAMES[game_msg.id] = game

@client.on(events.NewMessage(pattern="^حجره ورقه مقص$"))
async def rps_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("حجره ورقه مقص"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
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
    try:
        if event.is_private or not await check_activation(event.chat_id): return
        if await is_globally_disabled("كويز"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
        if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
            
        question_data = random.choice(QUIZ_QUESTIONS)
        question, options, correct_answer = question_data["question"], question_data["options"].copy(), question_data["answer"]
        random.shuffle(options)
        
        buttons = []
        for opt in options:
            is_correct = "1" if opt == correct_answer else "0"
            buttons.append(Button.inline(opt, data=f"quiz:{is_correct}"))
            
        keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        
        # --- (تم التعديل هنا) ---
        quiz_msg = await event.reply(f"**يابه سؤال عالطاير 🚁... جاوب صح وشوفنا شطارتك:\n\n{question}**", buttons=keyboard)
        # تسجيل الكويز الفعال لتتبعه لاحقًا
        CURRENT_QUIZZES[quiz_msg.id] = {
            "correct_answer": correct_answer,
            "participants": set()
        }
    except Exception as e:
        logger.error(f"Unhandled exception in start_quiz_handler: {e}", exc_info=True)
        await event.reply("**عفوًا، حدث خطأ غير متوقع أثناء بدء لعبة الكويز.**")

@client.on(events.NewMessage(pattern="^محيبس$"))
async def start_mahbis_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("محيبس"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
    chat_id = event.chat_id
    if chat_id in MAHIBES_GAMES: return await event.reply("**اكو لعبة محيبس بعدها شغالة!**")
    player = await event.get_sender()
    winner_pos = random.randint(0, 4)
    MAHIBES_GAMES[chat_id] = {"player_id": player.id, "winner_pos": winner_pos}
    buttons = [Button.inline("✊", data=f"mahbis:guess:{i}") for i in range(5)]
    keyboard = [buttons]
    await event.reply(f"**💎 لعبة المحيبس!**\n\n**يا [{player.first_name}](tg://user?id={player.id})، المحيبس ضايع بوحدة من هاي الأيادي... وين تتوقع؟**", buttons=keyboard)
    await asyncio.sleep(30)
    if chat_id in MAHIBES_GAMES and MAHIBES_GAMES[chat_id]["winner_pos"] == winner_pos:
        del MAHIBES_GAMES[chat_id]
        await event.respond("**انتهى الوقت! ⏰ محد لزم المحيبس.**")

@client.on(events.NewMessage(pattern="^من سيربح المليون$"))
async def millionaire_start_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("من سيربح المليون"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")
    await start_millionaire_game(event)

@client.on(events.NewMessage(pattern="^ثنائي اليوم$"))
async def couple_of_the_day_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("ثنائي اليوم"): return await event.reply("**(هذا الامر تحت الصيانه حاليا)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة.**")

    now = datetime.now()
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        daily_couple_data = settings.get("daily_couple", {})
        
        if daily_couple_data and daily_couple_data.get("date") == now.strftime("%Y-%m-%d"):
            user1_id, user2_id = daily_couple_data["couple"][0], daily_couple_data["couple"][1]
            user1_name, user2_name = daily_couple_data["user1_name"], daily_couple_data["user2_name"]
            reply_text = f"**💍 | ثنائي اليوم هم:**\n\n**[{user1_name}](tg://user?id={user1_id}) + [{user2_name}](tg://user?id={user2_id})**\n\n**جربوا حظكم باجر! 😉**"
            return await event.reply(reply_text)

        msg = await event.reply("**جاري البحث عن أسعد شخصين... 🧐💞**")
        await asyncio.sleep(2)
        try:
            participants = await client.get_participants(event.chat_id)
            real_users = [u for u in participants if not u.bot and not u.deleted]
            if len(real_users) < 2: return await msg.edit("**ماكو أعضاء كافين! 😥**")
            user1, user2 = random.sample(real_users, 2)
            
            settings["daily_couple"] = {"couple": [user1.id, user2.id], "date": now.strftime("%Y-%m-%d"), "user1_name": user1.first_name, "user2_name": user2.first_name}
            chat.settings = settings
            flag_modified(chat, "settings")
            await session.commit()
            
            reply_text = f"**💍 | و ألف مبروك! ثنائي اليوم هم:**\n\n**<a href='tg://user?id={user1.id}'>{user1.first_name}</a> + <a href='tg://user?id={user2.id}'>{user2.first_name}</a>**\n\n**نتمنى لكم يوماً سعيداً! 🎉**"
            await msg.edit(reply_text, parse_mode='html')
        except Exception as e:
            await msg.edit(f"**صارت مشكلة: **\n`{e}`")
