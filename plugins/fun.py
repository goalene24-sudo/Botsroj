# plugins/fun.py
import random
from telethon import events, Button
from bot import client
from .utils import check_activation, JOKES, RIDDLES, QUOTES, db, is_command_enabled

# --- (جديد) قائمة أسئلة أمر "كت" ---
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
PERSONALITY_ANALYSIS = [
    "انت شخصية قيادية بالفطرة، بس مشكلتك تضيع الشاحن مالتك بكل مكان.",
    "قلبك طيب وحنون، بس من تجوع تصير شخص ثاني مندري منين جاي.",
    "تحب تساعد الناس، لدرجة مرات تساعدهم يخلصون أكلهم.",
    "انت ذكي وتلقطها عالطاير، بس اذا لگفتها لا ترجعها.",
    "عندك حس فكاهي عالي، بس محد يضحك غيرك على نكاتك.",
    "طموح وتحب توصل لأهدافك، خصوصاً اذا الهدف هو الثلاجة بالليل.",
    "انت إنسان عملي، اذا شفت اثنين يتعاركون تصورهم ستوري بدل متفاككهم.",
    "كريم وتحب تنطي، وأكثر شي تحب تنطيه هو رأيك بالمواضيع اللي متعرفها.",
    "تتميز بالهدوء والصبر، خصوصاً من تنتظر النت يحمّل.",
    "عندك كاريزما وجاذبية، بس للأسف بس البعوض ينجذبلك.",
    "انت شخص اجتماعي وتحب الطلعات، بس من يجي وقت الحساب تسوي نفسك ميت.",
    "مخلص لأصدقائك، ومستعد توگفلهم بأي مشكلة... طالما هي مو مشكلة فلوس."
]


# --- معالجات الأوامر الترفيهية ---

@client.on(events.NewMessage(pattern=r"^حللني$"))
async def analyze_me_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "حللني" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    if not is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    sender = await event.get_sender()
    analysis = random.choice(PERSONALITY_ANALYSIS)
    await event.reply(f"**🤔 جاري تحليل شخصيتك يا [{sender.first_name}](tg://user?id={sender.id})...**\n\n**النتيجة:**\n**{analysis}**")

@client.on(events.NewMessage(pattern=r"^حلل$"))
async def analyze_user_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "حلل" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    if not is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لازم تسوي رپلَي على رسالة الشخص حتى أحلله.**")
    user_to_analyze = await reply.get_sender()
    analysis = random.choice(PERSONALITY_ANALYSIS)
    await event.reply(f"**🤔 جاري تحليل شخصية [{user_to_analyze.first_name}](tg://user?id={user_to_analyze.id})...**\n\n**النتيجة:**\n**{analysis}**")

@client.on(events.NewMessage(pattern="^نكتة$"))
async def joke_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "نكتة" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    if not is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    await event.reply(f"**{random.choice(JOKES)}**")

@client.on(events.NewMessage(pattern="^حزورة$"))
async def riddle_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "حزورة" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    if not is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    riddle_index, (riddle_q, riddle_a) = random.choice(list(enumerate(RIDDLES)))
    buttons = Button.inline("إظهار الجواب", data=f"riddle:{riddle_index}")
    await event.reply(f"**🤔 حزورة اليوم:**\n\n**{riddle_q}**", buttons=buttons)

@client.on(events.NewMessage(pattern="^كت$"))
async def kat_tweet_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "كت" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    if not is_command_enabled(event.chat_id, "games_enabled"): 
        return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    
    # اختيار سؤال عشوائي من القائمة الجديدة
    random_question = random.choice(KAT_QUESTIONS)
    
    # الرد على المستخدم بالسؤال
    await event.reply(f"**{random_question}**")

@client.on(events.NewMessage(pattern="^اقتباس$"))
async def quote_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    # --- التحقق إذا كان الأمر معطلاً بشكل عام ---
    disabled_cmds = db.get("global_settings", {}).get("disabled_cmds", [])
    if "اقتباس" in disabled_cmds:
        await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        return
    # --- نهاية التحقق ---
    if not is_command_enabled(event.chat_id, "games_enabled"): return await event.reply("🚫 | **عذراً، الألعاب معطلة في هذه المجموعة حالياً.**")
    quote = random.choice(QUOTES)
    await event.reply(f"**حكمة اليوم من سُـرُوچ تقول:**\n\n**📜 {quote}**\n\n**شلونها هاي؟ 😉**")
