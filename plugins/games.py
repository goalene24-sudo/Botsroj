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
from models import GlobalSetting, User, RPSGame # <-- تمت إضافة RPSGame
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, add_points, XO_GAMES, build_xo_keyboard, check_xo_winner, is_command_enabled, get_or_create_user, get_global_setting
from .quiz_data import QUIZ_QUESTIONS
from .millionaire import start_game as start_millionaire_game
import logging

logger = logging.getLogger(__name__)

# --- متغيرات خاصة بالألعاب (لا تحتاج قاعدة بيانات) ---
MAHIBES_GAMES = {}
CURRENT_QUIZZES = {}
RPS_GAMES = {} # <-- سيبقى هذا حاليًا لكن اللعبة لن تستخدمه بعد الآن
LUCK_BOX_MESSAGES = [
    "فتحت الصندوق و لگيت بي ورقة مكتوب عليها 'حاول مرة أخرى'... بس الخط حلو!",
    "الصندوق طلع فارغ، بس بي ريحة دولمة. بالعافية عاللي أكلها قبلك.",
    "مبروك! لگيت بالصندوق دعاء الوالدة، وهذا أحسن من كل الكنوز.",
    "لكيت بالصندوق جيس جبس أبو الكتاكيت... ألف عافية!",
    "للأسف لگيت بس رسالة من حبيبتك القديمة... شكلها بعدها متذكرتك.",
]

async def is_globally_disabled(command_name):
    disabled_list = await get_global_setting("disabled_cmds", [])
    return command_name in disabled_list

@client.on(events.NewMessage(pattern="^صندوق الحظ$"))
async def luck_box_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
        
    chat_id, user_id, COOLDOWN, current_time = event.chat_id, event.sender_id, 10 * 60 * 60, int(time.time())
    async with AsyncDBSession() as session:
        user = await get_or_create_user(session, chat_id, user_id)
        inventory = user.inventory or {}
        last_claim = inventory.get("luck_box_claim", 0)
        
        if current_time - last_claim < COOLDOWN:
            remaining_seconds = COOLDOWN - (current_time - last_claim)
            remaining_time_str = str(timedelta(seconds=int(remaining_seconds))).split('.')[0]
            return await event.reply(f"**على كيفك يمعود 🏃‍♂️... صندوقك الجاي يفتح بعد: {remaining_time_str} ⏳**")
            
        opening_msg = await event.reply("**بسم الله... جاي نفتح الصندوق... يا رب يطلع بي شي زين! 🤔🎁**")
        await asyncio.sleep(2)
        
        inventory["luck_box_claim"] = current_time
        user.inventory = inventory
        flag_modified(user, "inventory")
        
        rewards, probabilities = ["points", "message", "nothing"], [0.60, 0.25, 0.15]
        chosen_reward = random.choices(rewards, probabilities)[0]
        
        if chosen_reward == "points":
            points = random.randint(10, 75)
            await add_points(chat_id, user_id, points)
            await opening_msg.edit(f"**كفووو! 🤩 حظك كاعد ولكيت بالصندوق {points} نقطة!**")
        elif chosen_reward == "message":
            await opening_msg.edit(f"**فتحت الصندوق و... 🤔\n\n{random.choice(LUCK_BOX_MESSAGES)}**")
        else:
            await opening_msg.edit("**بووووم! 💣 الصندوق طلع فارغ هل مرة 😥... حظ أوفر يا بطل!**")
            
        await session.commit()

@client.on(events.NewMessage(pattern="^حظي$"))
async def slot_machine_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
        
    emojis = ["🍓", "🍉", "🍇", "🍌", "🍋", "🍒", "🏆"]
    a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    
    slot_msg = await event.reply("**جاي نسحب المكينة... يا رب حظ حلو! 🎰**")
    await asyncio.sleep(1); await slot_msg.edit(f"**[ {a} | ❓ | ❓ ]**")
    await asyncio.sleep(1); await slot_msg.edit(f"**[ {a} | {b} | ❓ ]**")
    await asyncio.sleep(1)
    
    if a == b == c:
        points_to_win = 500 if a == "🏆" else 100
        await add_points(event.chat_id, event.sender_id, points_to_win)
        result_text = f"**[ {a} | {b} | {c} ]**\n\n**حظكككك ناااار! 🥳 ربحت {points_to_win} نقطة! عاش يا كاطع!**"
    else:
        result_text = f"**[ {a} | {b} | {c} ]**\n\n**راحت عليك هل مرة... جرب مرة لخ بلكي تضبط وياك 😂**"
        
    await slot_msg.edit(result_text)

@client.on(events.NewMessage(pattern="^xo$"))
async def xo_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: 
        return await event.reply("**يمعود رپلَي على واحد حتى تلعبون!**")
        
    player1, player2 = await event.get_sender(), await reply.get_sender()
    if player1.id == player2.id: 
        return await event.reply("**تلعب ويه نفسك؟ شنو فلمك؟ 😐**")
    if player2.bot: 
        return await event.reply("**البوتات متلعب XO، شوفلك واحد من الكروب.**")
        
    game = {'board': ['-'] * 9, 'player_x': player1.id, 'player_o': player2.id, 'turn': player1.id, 'symbol': 'X', 'p1_name': player1.first_name, 'p2_name': player2.first_name}
    board_buttons = build_xo_keyboard(game['board'])
    game_msg = await event.reply(f"**⚔️ لعبة XO بدت! يلا يا أبطال!**\n\n**- لاعب 𝚇:** [{player1.first_name}](tg://user?id={player1.id})\n**- لاعب 𝙾:** [{player2.first_name}](tg://user?id={player2.id})\n\n**هسه السرة مال {player1.first_name} (𝚇)، شوفنا لعبك!**", buttons=board_buttons)
    XO_GAMES[game_msg.id] = game

# --- (تم التعديل بالكامل لاستخدام قاعدة البيانات) ---
@client.on(events.NewMessage(pattern="^حجره ورقه مقص$"))
async def rps_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: 
        return await event.reply("**رپلَي على واحد حتى تتحاداه!**")
        
    player1, player2 = await event.get_sender(), await reply.get_sender()
    if player1.id == player2.id: 
        return await event.reply("**شنو السالفة، تريد تتحده نفسك؟ 😂**")
    if player2.bot: 
        return await event.reply("**البوتات متلعب هاي السوالف، شوفلك عضو.**")

    # إرسال الرسالة والحصول على ID الخاص بها
    challenge_msg = await event.reply(
        f"**⚔️ تحدي كبييير!**\n\n"
        f"**[{player1.first_name}](tg://user?id={player1.id}) يتحدى [{player2.first_name}](tg://user?id={player2.id})!**\n\n"
        f"**يلا كل واحد بيكم يختار على السريع... 👀**"
    )
    msg_id = challenge_msg.id

    # إنشاء وتخزين اللعبة في قاعدة البيانات
    new_game = RPSGame(
        message_id=msg_id,
        chat_id=event.chat_id,
        player1_id=player1.id,
        player2_id=player2.id,
        player1_name=player1.first_name,
        player2_name=player2.first_name
    )
    async with AsyncDBSession() as session:
        session.add(new_game)
        await session.commit()

    # إنشاء الأزرار (لم نعد بحاجة لتضمين ID الرسالة هنا)
    buttons = [[
        Button.inline("🗿 حجرة", data=f"rps:rock:{player1.id}:{player2.id}"),
        Button.inline("📄 ورقة", data=f"rps:paper:{player1.id}:{player2.id}"),
        Button.inline("✂️ مقص", data=f"rps:scissors:{player1.id}:{player2.id}")
    ]]
    
    # تعديل الرسالة لإضافة الأزرار
    await challenge_msg.edit(challenge_msg.text, buttons=buttons)


@client.on(events.NewMessage(pattern="^كويز$"))
async def start_quiz_handler(event):
    try:
        if event.is_private or not await check_activation(event.chat_id): return
        if not await is_command_enabled(event.chat_id, "games_enabled"): 
            return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
            
        question_data = random.choice(QUIZ_QUESTIONS)
        question, options, correct_answer = question_data["question"], question_data["options"].copy(), question_data["answer"]
        random.shuffle(options)
        
        buttons = [Button.inline(opt, data=f"quiz:{'1' if opt == correct_answer else '0'}") for opt in options]
        keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        
        quiz_msg = await event.reply(f"**يابه سؤال عالطاير 🚁... جاوب صح وشوفنا شطارتك:\n\n{question}**", buttons=keyboard)
        CURRENT_QUIZZES[quiz_msg.id] = {"correct_answer": correct_answer, "participants": set()}
        
    except Exception as e:
        logger.error(f"Unhandled exception in start_quiz_handler: {e}", exc_info=True)
        await event.reply("**عفوًا، صارت مشكلة من ردت اسويلكم كويز 😥.**")

@client.on(events.NewMessage(pattern="^محيبس$"))
async def start_mahbis_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
        
    chat_id = event.chat_id
    if chat_id in MAHIBES_GAMES: 
        return await event.reply("**اكو لعبة محيبس بعدها شغالة، على كيفكم وحدة وحدة!**")
        
    player = await event.get_sender()
    winner_pos = random.randint(0, 4)
    MAHIBES_GAMES[chat_id] = {"player_id": player.id, "winner_pos": winner_pos}
    buttons = [Button.inline("✊", data=f"mahbis:guess:{i}") for i in range(5)]
    keyboard = [buttons]
    
    await event.reply(f"**💎 لعبة المحيبس!**\n\n**يا [{player.first_name}](tg://user?id={player.id})، المحيبس ضايع بوحدة من هاي الأيادي... وين تتوقع؟ طلعه يا كاطع!**", buttons=keyboard)
    await asyncio.sleep(30)
    
    if chat_id in MAHIBES_GAMES and MAHIBES_GAMES[chat_id]["winner_pos"] == winner_pos:
        del MAHIBES_GAMES[chat_id]
        await event.respond("**خلص الوقت! ⏰ محد لزم المحيبس، راحت عليكم.**")

@client.on(events.NewMessage(pattern="^من سيربح المليون$"))
async def millionaire_start_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")
    await start_millionaire_game(event)

@client.on(events.NewMessage(pattern="^ثنائي اليوم$"))
async def couple_of_the_day_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not await is_command_enabled(event.chat_id, "games_enabled"):
        return await event.reply("🚫 | **الادمنية طافين الألعاب بالكروب حالياً.**")

    now = datetime.now()
    async with AsyncDBSession() as session:
        chat = await get_or_create_chat(session, event.chat_id)
        settings = chat.settings or {}
        daily_couple_data = settings.get("daily_couple", {})
        
        if daily_couple_data and daily_couple_data.get("date") == now.strftime("%Y-%m-%d"):
            user1_id, user2_id = daily_couple_data["couple"][0], daily_couple_data["couple"][1]
            user1_name, user2_name = daily_couple_data["user1_name"], daily_couple_data["user2_name"]
            reply_text = f"**💍 | ثنائي اليوم همه نفسهم، بعدهم الكبلات:**\n\n**[{user1_name}](tg://user?id={user1_id}) + [{user2_name}](tg://user?id={user2_id})**\n\n**تعالو باجر نشوف منو راح يكونون كبلات الكروب الجدد! 😉**"
            return await event.reply(reply_text)

        msg = await event.reply("**جاي ندور على أسعد ثنين بالكروب... 🧐💞**")
        await asyncio.sleep(2)
        try:
            participants = await client.get_participants(event.chat_id)
            real_users = [u for u in participants if not u.bot and not u.deleted]
            if len(real_users) < 2: 
                return await msg.edit("**الكروب بي بس عينتين، شلون ازاوجهم! 😥**")
                
            user1, user2 = random.sample(real_users, 2)
            
            settings["daily_couple"] = {"couple": [user1.id, user2.id], "date": now.strftime("%Y-%m-%d"), "user1_name": user1.first_name, "user2_name": user2.first_name}
            chat.settings = settings
            flag_modified(chat, "settings")
            await session.commit()
            
            reply_text = f"**💍 | و ألف مبروك! ثنائي اليوم السعيد همه:**\n\n**<a href='tg://user?id={user1.id}'>{user1.first_name}</a> ❤️ <a href='tg://user?id={user2.id}'>{user2.first_name}</a>**\n\n**نتمنالكم يوم كله حب! 🎉**"
            await msg.edit(reply_text, parse_mode='html')
        except Exception as e:
            await msg.edit(f"**صارت مشكلة وماكدرت اختار ثنائي: **\n`{e}`")
