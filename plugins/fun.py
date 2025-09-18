import random
import time
import asyncio
import json
from telethon import events, Button
from telethon.errors.rpcerrorlist import UserNotParticipantError

from bot import client

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
from database import AsyncDBSession
from models import User, GlobalSetting

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, add_points, PERCENT_COMMANDS, JOKES, RIDDLES, QUOTES, is_command_enabled
from .utils import get_or_create_user

# --- بيانات الألعاب والهمس (لا تحتاج قاعدة بيانات) ---
WHISPERS = {}
PROPOSALS = {}
DICE_GAMES = {}
BLESS_COUNTERS = {}
WYR_GAMES = {}

INTERACTIVE_ACTIONS = {
    "صفعة": "👋 | {user1} قام بصفع {user2}!",
    "بوسة": "😘 | {user1} أرسل قبلة إلى {user2}!",
    "عناق": "🤗 | {user1} قام بمعانقة {user2}!",
    "غمزة": "😉 | {user1} غمز لـ {user2}!",
    "قتل": "🔪 | {user1} قام بقتل {user2} بدم بارد!",
    "رزالة": "😡 | {user1} أنطى رزالة محترمة لـ {user2}!",
}
KAT_QUESTIONS = [
    "ما هي طريقتك في الحصول على الراحة النفسية؟",
    "كم ساعة تنام في اليوم؟",
    "ما هو رأيك بصداقة البنت والولد إلكترونياً؟",
    "هل تمحي العشرة الطيبة عشان موقف ماعجبك أو سوء فهم؟",
    "لو خيروك بين المال الوفير والحب الحقيقي، ماذا تختار؟",
    "ما هو أكثر شيء تفتخر به في حياتك؟",
    "ما هي أجمل ذكرى عالقة في ذهنك من الطفولة؟",
    "ما هي العادة التي تتمنى أن تتخلص منها؟",
    "ما هو الفيلم أو المسلسل الذي تستطيع مشاهدته مراراً وتكراراً؟",
    "لو كان بإمكانك السفر إلى أي مكان في العالم الآن، أين ستذهب؟",
    "ما هو الشيء الذي لا يمكن أن تسامح فيه أبداً؟",
    "ما هي أهم صفة تبحث عنها في الصديق؟",
    "ما هو أكبر حلم تتمنى تحقيقه؟",
    "أفضل وجبة أكلتها في حياتك؟",
    "هل تعتقد أن وسائل التواصل الاجتماعي قربت الناس أم أبعدتهم؟",
    "ما هو الدرس الذي تعلمته بالطريقة الصعبة؟",
    "لو امتلكت قوة خارقة ليوم واحد، ماذا ستكون وماذا ستفعل بها؟",
    "ما هو الكتاب الذي أثر فيك كثيراً؟",
    "هل تفضل أن تعرف المستقبل أم أن تغير الماضي؟",
    "ما هو الشيء الذي يجعلك تبتسم دائماً؟"
]
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
    {"q": "تعيش بدون انترنت لو بدون أصدقاء؟", "o1": "بدون انترنت 🌐", "o2": "بدون أصدقاء 🧍"},
    {"q": "تأكل أكل ما تحبه طول حياتك لو تسمع أغنية ما تحبها طول حياتك؟", "o1": "أكل ما أحبه 🤢", "o2": "أغنية ما أحبها 🎶"},
    {"q": "القدرة على الطيران لو القدرة على أن تكون غير مرئي؟", "o1": "الطيران 🕊️", "o2": "غير مرئي 👻"},
    {"q": "أن تتكلم مع الحيوانات لو أن تتكلم كل لغات العالم؟", "o1": "كلام الحيوانات 🐕", "o2": "كل اللغات 🗣️"},
    {"q": "أن تمتلك 10 مليون دولار الآن لو أن تعود لسن 10 سنوات مع كل معرفتك الحالية؟", "o1": "10 مليون دولار 💰", "o2": "أعود طفل 👶"},
]
PERSONALITY_ANALYSIS = [
    "انت شخصية قيادية بالفطرة، بس مشكلتك تضيع الشاحن مالتك بكل مكان.",
    "قلبك طيب وحنون، بس من تجوع تصير شخص ثاني مندري منين جاي.",
    "تحب تساعد الناس، لدرجة مرات تساعدهم يخلصون أكلهم.",
    "انت ذكي وتلقطها عالطاير، بس اذا لگفتها لا ترجعها.",
    "عندك حس فكاهي عالي، بس محد يضحك غيرك على نكاتك.",
    "طموح وتحب توصل لأهدافك، خصوصاً اذا الهدف هو الثلاجة بالليل.",
]

async def is_globally_disabled(command_name):
    async with AsyncDBSession() as session:
        result = await session.execute(
            select(GlobalSetting).where(GlobalSetting.key == "disabled_cmds")
        )
        setting = result.scalar_one_or_none()
        if setting and setting.value:
            try:
                disabled_list = json.loads(setting.value)
                return command_name in disabled_list
            except (json.JSONDecodeError, TypeError):
                return False
        return False

@client.on(events.NewMessage(pattern="^لو خيروك$"))
async def wyr_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("لو خيروك"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    question_data = random.choice(WOULD_YOU_RATHER_QUESTIONS)
    q, o1, o2 = question_data["q"], question_data["o1"], question_data["o2"]
    
    message_text = f"🤔 **لعبة لو خيروك** 🤔\n\n**{q}**"
    buttons = [
        [Button.inline(f"{o1} (0)", data=f"wyr:1")],
        [Button.inline(f"{o2} (0)", data=f"wyr:2")]
    ]
    
    game_msg = await event.reply(message_text, buttons=buttons)
    WYR_GAMES[game_msg.id] = {"q": q, "o1": o1, "o2": o2, "v1": 0, "v2": 0, "users": set()}

@client.on(events.NewMessage(pattern=r"^حللني$"))
async def analyze_me_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("حللني"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    sender = await event.get_sender()
    analysis = random.choice(PERSONALITY_ANALYSIS)
    await event.reply(f"**🤔 جاري تحليل شخصيتك يا [{sender.first_name}](tg://user?id={sender.id})...**\n\n**النتيجة:**\n**{analysis}**")

@client.on(events.NewMessage(pattern=r"^حلل$"))
async def analyze_user_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("حلل"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص حتى أحلله.**")
    user_to_analyze = await reply.get_sender()
    analysis = random.choice(PERSONALITY_ANALYSIS)
    await event.reply(f"**🤔 جاري تحليل شخصية [{user_to_analyze.first_name}](tg://user?id={user_to_analyze.id})...**\n\n**النتيجة:**\n**{analysis}**")

@client.on(events.NewMessage(pattern="^نكتة$"))
async def joke_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("نكتة"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    await event.reply(f"**{random.choice(JOKES)}**")

@client.on(events.NewMessage(pattern="^حزورة$"))
async def riddle_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("حزورة"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    riddle_index, (riddle_q, riddle_a) = random.choice(list(enumerate(RIDDLES)))
    buttons = Button.inline("إظهار الجواب", data=f"riddle:{riddle_index}")
    await event.reply(f"**🤔 حزورة اليوم:**\n\n**{riddle_q}**", buttons=buttons)

@client.on(events.NewMessage(pattern="^كت$"))
async def kat_tweet_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("كت"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    question = random.choice(KAT_QUESTIONS)
    await event.reply(f"**🤔 | سؤال للنقاش:**\n\n**- {question}**")

@client.on(events.NewMessage(pattern=f"^({'|'.join(PERCENT_COMMANDS)})$"))
async def percent_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    command_name = event.raw_text.lower()
    if await is_globally_disabled(command_name):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "social_commands_enabled"): 
        return await event.reply("🚫 | **عذراً، الأوامر الاجتماعية معطلة في هذه المجموعة حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**رپلَي على واحد حتى اگلك شگد النسبة.**")
    sender, replied_user = await event.get_sender(), await reply.get_sender()
    if sender.id == replied_user.id: return await event.reply("**لك بابا متگدر تسويها على نفسك!**")
    percent, percent_type = random.randint(1, 100), event.raw_text.replace("نسبة ", "")
    await event.reply(f"**نسبة {percent_type} بين [{sender.first_name}](tg://user?id={sender.id}) و [{replied_user.first_name}](tg://user?id={replied_user.id}) هي:**\n\n`{percent}%` 😏")

@client.on(events.NewMessage(pattern="^الترتيب$"))
async def leaderboard_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("الترتيب"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")

    async with AsyncDBSession() as session:
        result = await session.execute(
            select(User)
            .where(User.chat_id == event.chat_id, User.points > 0)
            .order_by(User.points.desc())
            .limit(10)
        )
        sorted_users = result.scalars().all()

    if not sorted_users: 
        return await event.reply("**بعدكم كلكم صفر، منو ارتبه؟ 🤔**")

    leaderboard_text = "**🌟 أبطال المجموعة (حسب النقاط):** 🌟\n\n"
    for i, user_data in enumerate(sorted_users, 1):
        try:
            user_entity = await client.get_entity(user_data.user_id)
            user_name = user_entity.first_name
        except (ValueError, UserNotParticipantError):
            user_name = f"عضو سابق"
            
        points = user_data.points
        if i == 1: medal = "🥇"
        elif i == 2: medal = "🥈"
        elif i == 3: medal = "🥉"
        else: medal = f"`{i}`."
        leaderboard_text += f"**{medal} [{user_name}](tg://user?id={user_data.user_id}) - `{points}` نقطة**\n"
        
    await event.reply(leaderboard_text)

@client.on(events.NewMessage(pattern="^زواج$"))
async def ship_game_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("زواج"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "social_commands_enabled"): 
        return await event.reply("🚫 | **عذراً، الأوامر الاجتماعية معطلة في هذه المجموعة حالياً.**")
        
    loading_msg = await event.reply("**💍 دا أشوف منو متوالم... لحظة...**")
    try:
        participants = await client.get_participants(event.chat_id)
        users = [user for user in participants if not user.bot and not user.deleted]
        if len(users) < 2: return await loading_msg.edit("**ماكو أعضاء كافيين حتى أزوجهم. 😂**")
        p1, p2 = random.sample(users, 2)
        ship_msg = await event.reply(f"**💍 إعلان زواج رسمي!** 💍\n\n**بعد دراسة وتفكير عميق، تم تزويج:**\n\n**العريس:** [{p1.first_name}](tg://user?id={p1.id})\n**العروس:** [{p2.first_name}](tg://user?id={p2.id})\n\n**باركولهم يمعودين! 🥳**", buttons=Button.inline("مباركين 🎉 (0)", data=f"bless:{event.chat_id}:{event.id}"))
        await loading_msg.delete()
        BLESS_COUNTERS[ship_msg.id] = {"count": 0, "users": set()}
    except Exception as e: 
        await loading_msg.edit(f"**ماصارت القسمة، اكو مشكلة: {e}**")

@client.on(events.NewMessage(pattern="^اقتباس$"))
async def quote_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("اقتباس"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
    quote = random.choice(QUOTES)
    await event.reply(f"**حكمة اليوم من سُـرُوچ تقول:**\n\n**📜 {quote}**\n\n**شلونها هاي؟ 😉**")

# --- تم تعديل هذه الدالة بالكامل ---
@client.on(events.NewMessage(pattern=r"^همس(?: |$)(.*)"))
async def whisper_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("همس"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "social_commands_enabled"): 
        return await event.reply("🚫 | **عذراً، الأوامر الاجتماعية معطلة في هذه المجموعة حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لازم ترد على رسالة الشخص اللي تريد تهمسله.**")
    
    sender = await event.get_sender()
    receiver = await reply.get_sender()

    if sender.id == receiver.id: return await event.reply("**تهمس لنفسك؟ شدعوة! 😂**")
    
    # طريقة جديدة وموثوقة لاستخلاص النص
    whisper_text = event.pattern_match.group(1).strip()

    if not whisper_text: 
        return await event.reply("**شنو الهمسة؟ اكتب رسالتك بعد كلمة `همس`.**\n\n**مثال: `همس شلونك`**")
    
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
    command_name = event.raw_text.lower()
    if await is_globally_disabled(command_name):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "social_commands_enabled"): 
        return await event.reply("🚫 | **عذراً، الأوامر الاجتماعية معطلة في هذه المجموعة حالياً.**")
        
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**هذا الأمر لازم تستخدمه بالرد على شخص.**")
    
    sender = await event.get_sender()
    receiver = await reply.get_sender()

    if sender.id == receiver.id:
        return await event.reply("**شدعوة هالنرجسية! متگدر تسويها لنفسك.**")
    
    async with AsyncDBSession() as session:
        receiver_user_obj = await get_or_create_user(session, event.chat_id, receiver.id)

    inventory = receiver_user_obj.inventory or {}
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
    command_name = event.pattern_match.group(1).lower()
    if await is_globally_disabled(command_name):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "social_commands_enabled"): 
        return await event.reply("🚫 | **عذراً، الأوامر الاجتماعية معطلة في هذه المجموعة حالياً.**")
        
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
        "proposer_id": proposer.id, "proposer_name": proposer.first_name,
        "proposed_id": proposed.id, "proposed_name": proposed.first_name
    }

@client.on(events.NewMessage(pattern=r"^من هو$"))
async def who_is_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("من هو"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
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
    if await is_globally_disabled("تحدي نرد"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
    if not await is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
        
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

@client.on(events.CallbackQuery(pattern=b"^wyr:"))
async def wyr_callback_handler(event):
    game_id = event.message_id
    if game_id not in WYR_GAMES:
        return await event.answer("هذه اللعبة قديمة جداً!", alert=True)

    game = WYR_GAMES[game_id]
    user_id = event.sender_id

    if user_id in game["users"]:
        return await event.answer("لقد قمت بالتصويت بالفعل!", alert=True)

    game["users"].add(user_id)
    choice = int(event.data.decode().split(":")[1])

    if choice == 1:
        game["v1"] += 1
    else: # choice == 2
        game["v2"] += 1

    new_buttons = [
        [Button.inline(f'{game["o1"]} ({game["v1"]})', data="wyr:1")],
        [Button.inline(f'{game["o2"]} ({game["v2"]})', data="wyr:2")]
    ]

    try:
        await event.edit(buttons=new_buttons)
    except Exception:
        pass
