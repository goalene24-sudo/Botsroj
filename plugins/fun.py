# plugins/fun.py
import random
import time
from telethon import events, Button
from telethon.tl.types import InputMediaDice
from bot import client
from .utils import check_activation, add_points, PERCENT_COMMANDS, JOKES, RIDDLES, QUOTES, is_admin, db, save_db, BLESS_COUNTERS
from telethon.errors.rpcerrorlist import UserNotParticipantError
import config

# --- بيانات الألعاب والهمس ---
WHISPERS = {}
PROPOSALS = {}
DICE_GAMES = {} 
INTERACTIVE_ACTIONS = {
    "صفعة": "👋 | {user1} قام بصفع {user2}!",
    "بوسة": "😘 | {user1} أرسل قبلة إلى {user2}!",
    "عناق": "🤗 | {user1} قام بمعانقة {user2}!",
    "غمزة": "😉 | {user1} غمز لـ {user2}!",
    "قتل": "🔪 | {user1} قام بقتل {user2} بدم بارد!",
    "رزالة": "😡 | {user1} أنطى رزالة محترمة لـ {user2}!",
}
WHO_IS_QUESTIONS = [
    "من هو أذكى شخص بالمجموعة؟ 🤓", "من هو أكثر واحد ينام؟ 😴",
    "من هو أكثر واحد يحب الأكل؟ 🍔", "من هو أغنى واحد راح يصير بالمستقبل؟ 💰",
    "من هو أكثر واحد حشاش؟ 😂", "من هو ملك الدراما؟ 🎭",
    "من هو أكثر واحد محظوظ؟ 🍀", "من هو أكثر واحد يحب السفر؟ ✈️",
    "من هو أكثر واحد رياضي؟ 💪", "من هو اللي ماخذ مقلب بنفسه؟ 😎",
    "من هو اللي راح يتزوج أول واحد؟ 💍", "من هو أكثر واحد غامض؟ 🤫",
    "من هو اللي دائماً جوعان؟ 🍕", "من هو اللي عنده أحلى ضحكة؟ 😄",
    "من هو اللي ما يرد بسرعة؟ 🐌", "من هو اللي عنده أسوأ حظ؟ ⛈️"
]
WOULD_YOU_RATHER_QUESTIONS = [
    {"q": "تعيش بدون انترنت لو بدون أصدقاء؟", "o1": "بدون انترنت 🌐", "o2": "بدون أصدقاء 🧍"}, {"q": "تآكل أكل ما تحبه طول حياتك لو تسمع أغنية ما تحبها طول حياتك؟", "o1": "أكل ما أحبه 🤢", "o2": "أغنية ما أحبها 🎶"},
]
WYR_GAMES = {}
PERSONALITY_ANALYSIS = [
     "انت شخصية قيادية بالفطرة، بس مشكلتك تضيع الشاحن مالتك بكل مكان.", "قلبك طيب وحنون، بس من تجوع تصير شخص ثاني مندري منين جاي.",
]

# --- معالجات الأوامر الترفيهية ---
@client.on(events.NewMessage(pattern="^لو خيروك$"))
async def wyr_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    question_data = random.choice(WOULD_YOU_RATHER_QUESTIONS)
    q, o1, o2 = question_data["q"], question_data["o1"], question_data["o2"]
    buttons = [[Button.inline(f"{o1} (0)", data=f"wyr:1"), Button.inline(f"{o2} (0)", data=f"wyr:2")]]
    game_msg = await event.reply(f"**🤔 لو خيروك:**\n\n**{q}**", buttons=buttons)
    WYR_GAMES[game_msg.id] = {"q": q, "o1": o1, "o2": o2, "v1": 0, "v2": 0, "users": set()}

@client.on(events.NewMessage(pattern=r"^حللني$"))
async def analyze_me_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    sender = await event.get_sender()
    analysis = random.choice(PERSONALITY_ANALYSIS)
    await event.reply(f"**🤔 جاري تحليل شخصيتك يا [{sender.first_name}](tg://user?id={sender.id})...**\n\n**النتيجة:**\n**{analysis}**")

@client.on(events.NewMessage(pattern=r"^حلل$"))
async def analyze_user_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص حتى أحلله.**")
    user_to_analyze = await reply.get_sender()
    analysis = random.choice(PERSONALITY_ANALYSIS)
    await event.reply(f"**🤔 جاري تحليل شخصية [{user_to_analyze.first_name}](tg://user?id={user_to_analyze.id})...**\n\n**النتيجة:**\n**{analysis}**")

@client.on(events.NewMessage(pattern="^نكتة$"))
async def joke_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    await event.reply(f"**{random.choice(JOKES)}**")

@client.on(events.NewMessage(pattern="^حزورة$"))
async def riddle_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    riddle_index, (riddle_q, riddle_a) = random.choice(list(enumerate(RIDDLES)))
    buttons = Button.inline("إظهار الجواب", data=f"riddle:{riddle_index}")
    await event.reply(f"**🤔 حزورة اليوم:**\n\n**{riddle_q}**", buttons=buttons)

@client.on(events.NewMessage(pattern="^كت$"))
async def kat_tweet_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    loading_msg = await event.reply("**🔄 دا أفكر بضحايا جدد...**")
    try:
        participants = await client.get_participants(event.chat_id)
        users = [user for user in participants if not user.bot and not user.deleted]
        if len(users) < 2: return await loading_msg.edit("**ماكو أعضاء كافيين حتى الزمهم لزمة حلوة. 😂**")
        user1, user2 = random.sample(users, 2)
        quote = random.choice(QUOTES)
        kat_message = f"**{user1.first_name}**: ...\n**└ [{user2.first_name}](tg://user?id={user2.id})**: **{quote}**"
        await loading_msg.edit(kat_message)
    except Exception as e: await loading_msg.edit(f"**ماصارت اللعبة، اكو مشكلة: {e}**")

@client.on(events.NewMessage(pattern=f"^({'|'.join(PERCENT_COMMANDS)})$"))
async def percent_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**رپلَي على واحد حتى اگلك شگد النسبة.**")
    sender, replied_user = await event.get_sender(), await reply.get_sender()
    if sender.id == replied_user.id: return await event.reply("**لك بابا متگدر تسويها على نفسك!**")
    percent, percent_type = random.randint(1, 100), event.raw_text.replace("نسبة ", "")
    await event.reply(f"**نسبة {percent_type} بين [{sender.first_name}](tg://user?id={sender.id}) و [{replied_user.first_name}](tg://user?id={replied_user.id}) هي:**\n\n`{percent}%` 😏")

@client.on(events.NewMessage(pattern="^الترتيب$"))
async def leaderboard_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    chat_id_str = str(event.chat_id)
    users_data = db.get(chat_id_str, {}).get("users", {})
    if not users_data: return await event.reply("**بعدكم كلكم صفر، منو ارتبه؟ 🤔**")
    sorted_users = sorted(users_data.items(), key=lambda item: item[1].get("points", 0), reverse=True)
    leaderboard_text = "**🌟 أبطال المجموعة (حسب النقاط):** 🌟\n\n"
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        try:
            user = await client.get_entity(int(user_id))
            user_name = user.first_name
        except (ValueError, UserNotParticipantError): user_name = f"عضو سابق"
        points = data.get("points", 0)
        if i == 1: medal = "🥇"
        elif i == 2: medal = "🥈"
        elif i == 3: medal = "🥉"
        else: medal = f"`{i}`."
        leaderboard_text += f"**{medal} [{user_name}](tg://user?id={user_id}) - `{points}` نقطة**\n"
    await event.reply(leaderboard_text)

@client.on(events.NewMessage(pattern="^زواج$"))
async def ship_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    loading_msg = await event.reply("**💍 دا أشوف منو متوالم... لحظة...**")
    try:
        participants = await client.get_participants(event.chat_id)
        users = [user for user in participants if not user.bot and not user.deleted]
        if len(users) < 2: return await loading_msg.edit("**ماكو أعضاء كافيين حتى أزوجهم. 😂**")
        p1, p2 = random.sample(users, 2)
        ship_msg = await event.reply(f"**💍 إعلان زواج رسمي!** 💍\n\n**بعد دراسة وتفكير عميق، تم تزويج:**\n\n**العريس:** [{p1.first_name}](tg://user?id={p1.id})\n**العروس:** [{p2.first_name}](tg://user?id={p2.id})\n\n**باركولهم يمعودين! 🥳**", buttons=Button.inline("مباركين 🎉 (0)", data=f"bless:{event.chat_id}:{event.id}"))
        await loading_msg.delete()
        BLESS_COUNTERS[ship_msg.id] = {"count": 0, "users": set()}
    except Exception as e: await loading_msg.edit(f"**ماصارت القسمة، اكو مشكلة: {e}**")

@client.on(events.NewMessage(pattern="^اقتباس$"))
async def quote_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    quote = random.choice(QUOTES)
    await event.reply(f"**حكمة اليوم من سُـرُوچ تقول:**\n\n**📜 {quote}**\n\n**شلونها هاي؟ 😉**")

@client.on(events.NewMessage(pattern=r"^همس(?: (.*))?$"))
async def whisper_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لازم ترد على رسالة الشخص اللي تريد تهمسله.**")
    sender, receiver = await event.get_sender(), await reply.get_sender()
    if sender.id == receiver.id: return await event.reply("**تهمس لنفسك؟ شدعوة! 😂**")
    whisper_text = event.pattern_match.group(1)
    if not whisper_text: return await event.reply("**شنو الهمسة؟ اكتب رسالتك بعد كلمة `همس`.**")
    await event.delete()
    message_text = (
        f"**🤫 | همسة جديدة!**\n\n"
        f"**▫️ من:** [{sender.first_name}](tg://user?id={sender.id})\n"
        f"**▫️ إلى:** [{receiver.first_name}](tg://user?id={receiver.id})\n\n"
        f"**الرسالة مقفولة، بس المستلم يگدر يشوفها.**"
    )
    whisper_msg = await client.send_message(
        event.chat_id, message_text, buttons=Button.inline("🔒 إقرأ الهمسة", data="whisper:read")
    )
    WHISPERS[whisper_msg.id] = {"to_id": receiver.id, "text": whisper_text}

@client.on(events.NewMessage(pattern=f"^(?:{'|'.join(INTERACTIVE_ACTIONS.keys())})$"))
async def interactive_action_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**هذا الأمر لازم تستخدمه بالرد على شخص.**")
    
    sender = await event.get_sender()
    receiver = await reply.get_sender()

    if sender.id == receiver.id:
        return await event.reply("**شدعوة هالنرجسية! متگدر تسويها لنفسك.**")
    
    chat_id_str = str(event.chat_id)
    receiver_id_str = str(receiver.id)
    receiver_data = db.get(chat_id_str, {}).get("users", {}).get(receiver_id_str, {})
    inventory = receiver_data.get("inventory", {})
    immunity_data = inventory.get("حصانة")

    if immunity_data:
        purchase_time = immunity_data.get("purchase_time", 0)
        duration_seconds = immunity_data.get("duration_days", 0) * 86400

        if time.time() - purchase_time < duration_seconds:
            return await event.reply(f"**لا يمكن استخدام هذا الأمر ضد [{receiver.first_name}](tg://user?id={receiver.id})، فهو يمتلك درع حصانة! 🛡️**")

    action_text = event.raw_text
    response_template = INTERACTIVE_ACTIONS[action_text]
    
    response_message = response_template.format(
        user1=f"[{sender.first_name}](tg://user?id={sender.id})",
        user2=f"[{receiver.first_name}](tg://user?id={receiver.id})"
    )
    await event.reply(f"**{response_message}**")

@client.on(events.NewMessage(pattern=r"^(تزوجني|اخطبني)$"))
async def propose_marriage_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لمن تطلب الزواج؟ لازم ترد على رسالة الشخص.**")

    proposer = await event.get_sender()
    proposed = await reply.get_sender()

    if proposer.id == proposed.id:
        return await event.reply("**تريد تتزوج نفسك؟ 🤔**")
    if proposed.bot:
        return await event.reply("**ما أظن البوتات تتزوج. جرب شخص حقيقي.**")

    proposal_text = (
        f"**💍 طلب زواج رسمي!** 💍\n\n"
        f"**يا [{proposed.first_name}](tg://user?id={proposed.id})، "
        f"العضو [{proposer.first_name}](tg://user?id={proposer.id}) دتقدملك/چ. توافق/ين؟**"
    )
    
    buttons = [
        [
            Button.inline("💍 أوافق", data=f"proposal:accept:{proposer.id}:{proposed.id}"),
            Button.inline("💔 أرفض", data=f"proposal:reject:{proposer.id}:{proposed.id}")
        ]
    ]
    
    proposal_msg = await event.reply(proposal_text, buttons=buttons)
    PROPOSALS[proposal_msg.id] = {
        "proposer_id": proposer.id,
        "proposer_name": proposer.first_name,
        "proposed_id": proposed.id,
        "proposed_name": proposed.first_name
    }

@client.on(events.NewMessage(pattern=r"^من هو$"))
async def who_is_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    loading_msg = await event.reply("**دا أفكر وأختار... 🤔**")
    
    try:
        participants = await client.get_participants(event.chat_id)
        users = [user for user in participants if not user.bot and not user.deleted]
        
        if not users:
            return await loading_msg.edit("**ماكو أي أعضاء بالمجموعة حتى نلعب! 🙁**")
            
        chosen_user = random.choice(users)
        question = random.choice(WHO_IS_QUESTIONS)
        
        result_text = f"**{question}**\n\n**إنه بالتأكيد... [{chosen_user.first_name}](tg://user?id={chosen_user.id})! 😂**"
        await loading_msg.edit(result_text)

    except Exception as e:
        await loading_msg.edit(f"**ما گدرت ألعب، صارت مشكلة:\n`{e}`**")
        
@client.on(events.NewMessage(pattern="^تحدي نرد$"))
async def dice_challenge_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**تتحدى منو؟ لازم ترد على رسالة شخص.**")
    
    player1 = await event.get_sender()
    player2 = await reply.get_sender()
    
    if player1.id == player2.id: return await event.reply("**متگدر تتحدى نفسك!**")
    if player2.bot: return await event.reply("**البوتات متلعب هاي اللعبة.**")

    text = (
        f"**⚔️ تحدي نرد!** ⚔️\n\n"
        f"**المتحدي:** [{player1.first_name}](tg://user?id={player1.id})\n"
        f"**الخصم:** [{player2.first_name}](tg://user?id={player2.id})\n\n"
        f"**الدور على [{player1.first_name}](tg://user?id={player1.id}) لرمي النرد.**"
    )
    
    buttons = Button.inline("🎲 ارمِ النرد", data="dice_challenge:roll")
    
    game_msg = await event.reply(text, buttons=buttons)
    
    DICE_GAMES[game_msg.id] = {
        "p1_id": player1.id, "p1_name": player1.first_name, "p1_roll": None,
        "p2_id": player2.id, "p2_name": player2.first_name, "p2_roll": None,
        "turn": "p1"
    }
