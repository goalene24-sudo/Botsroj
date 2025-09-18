import httpx
import random
import json
import re
import html
from telethon import events, Button
from bot import client
from .utils import check_activation
from .hadith_data import HADITH_LIST
from .hisn_almuslim_data import HISN_ALMUSLIM

SEERAH_STAGES = {
    "birth": {
        "button": "📜 مولده ونشأته",
        "text": (
            "**مولده ونشأته الشريفة ﷺ**\n\n"
            "**وُلد النبي محمد ﷺ في مكة المكرمة يوم الاثنين من شهر ربيع الأول في 'عام الفيل'.** "
            "**والده هو عبد الله بن عبد المطلب، وتوفي قبل ولادته. والدته هي آمنة بنت وهب.** "
            "**نشأ يتيماً، فكفله جده عبد المطلب، وبعد وفاته كفله عمه أبو طالب.**\n\n"
            "**عُرف في شبابه بالصدق والأمانة، حتى لُقب بـ 'الصادق الأمين'.**"
        )
    },
    "revelation": {
        "button": "✨ البعثة النبوية",
        "text": (
            "**البعثة النبوية وبداية الوحي**\n\n"
            "**عندما بلغ النبي ﷺ الأربعين من عمره، كان يتعبد في غار حراء. وفي إحدى الليالي، نزل عليه أمين الوحي جبريل عليه السلام بأول آيات القرآن الكريم:** "
            "**\"اقْرأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ\".**\n\n"
            "**كانت هذه بداية نبوته ورسالته. بدأ دعوته سراً لمدة ثلاث سنوات، ثم أمره الله بالجهر بالدعوة.**"
        )
    },
    "hijrah": {
        "button": "✈️ الهجرة إلى المدينة",
        "text": (
            "**الهجرة النبوية إلى المدينة**\n\n"
            "**بعد أن اشتد أذى قريش على المسلمين في مكة، أذن الله لنبيه ﷺ وأصحابه بالهجرة إلى يثرب (المدينة المنورة).** "
            "**كانت الهجرة نقطة تحول كبرى في تاريخ الإسلام، حيث تم تأسيس أول دولة إسلامية، وآخى النبي ﷺ بين المهاجرين والأنصار.**"
        )
    },
    "battles": {
        "button": "⚔️ أبرز الغزوات",
        "text": (
            "**أبرز الغزوات في عهد النبي ﷺ**\n\n"
            "**خاض المسلمون بقيادة النبي ﷺ عدة غزوات دفاعاً عن الدين والدولة، من أبرزها:**\n"
            "**• غزوة بدر: أول انتصار كبير للمسلمين.**\n"
            "**• غزوة أحد: درس في الطاعة والصبر.**\n"
            "**• غزوة الخندق (الأحزاب): ظهرت فيها حكمة النبي ﷺ وصبر المؤمنين.**\n"
            "**• فتح مكة: تم بدون قتال تقريباً، وكان يوم عفو وتسامح.**"
        )
    },
    "farewell": {
        "button": "🕋 حجة الوداع ووفاته",
        "text": (
            "**حجة الوداع ووفاته ﷺ**\n\n"
            "**في السنة العاشرة للهجرة، حج النبي ﷺ حجته الوحيدة، وعُرفت بـ 'حجة الوداع'، وألقى فيها خطبته الشهيرة التي أرسى فيها قواعد الدين.**\n\n"
            "**بعد عودته إلى المدينة، مرض النبي ﷺ واشتد به المرض، وتوفي يوم الاثنين 12 ربيع الأول من السنة 11 هـ، ودُفن في حجرته الشريفة بجوار مسجده.**"
        )
    }
}

NAMES_OF_ALLAH = [
    {"name": "الله", "meaning": "الاسم الأعظم الذي تفرد به الحق سبحانه وخص به نفسه."},
    {"name": "الرحمن", "meaning": "واسع الرحمة الذي وسعت رحمته كل شيء."},
    {"name": "الرحيم", "meaning": "المُنعم أبدًا، المتفضل دومًا، الذي يرحم عباده المؤمنين."},
    {"name": "الملك", "meaning": "المتصرف في مُلكه كيف يشاء، والذي لا يحتاج لشيء."},
    {"name": "القدوس", "meaning": "الطاهر المنزه عن كل عيب ونقص."},
    {"name": "السلام", "meaning": "الذي سلِم من كل عيب، وواهب السلام لعباده."},
    {"name": "العزيز", "meaning": "الغالب الذي لا يُقهر."},
    {"name": "الجبار", "meaning": "الذي تنفذ مشيئته، ولا يخرج أحد عن تقديره."},
    {"name": "الخالق", "meaning": "المُبدع المُوجِد للأشياء من العدم."},
    {"name": "الغفار", "meaning": "الكثير المغفرة والستر لذنوب عباده."},
    {"name": "الوهاب", "meaning": "الكثير الهبات والعطايا بدون مقابل."},
    {"name": "الرزاق", "meaning": "المتكفل بأرزاق العباد، خالق الأرزاق وموصلها."},
    {"name": "الفتاح", "meaning": "الذي يفتح أبواب الرزق والرحمة لعباده."},
    {"name": "العليم", "meaning": "الذي يعلم كل شيء، لا تخفى عليه خافية."},
    {"name": "السميع", "meaning": "الذي يسمع كل الأصوات مهما خفيت."},
    {"name": "البصير", "meaning": "الذي يرى كل الأشياء مهما دقت وصغرت."},
    {"name": "اللطيف", "meaning": "البر بعباده، الذي يوصل إليهم مصالحهم بلطفه وإحسانه."},
    {"name": "الخبير", "meaning": "العالم بكنه الأشياء وحقائقها الخفية."},
    {"name": "الحليم", "meaning": "الذي لا يعاجل العاصين بالعقوبة، ويمهلهم ليتوبوا."},
    {"name": "العظيم", "meaning": "الذي بلغ الكمال المطلق في صفاته وجلاله."},
    {"name": "الغفور", "meaning": "الكثير المغفرة، الذي يستر الذنوب ويتجاوز عنها."},
    {"name": "الشكور", "meaning": "الذي يثيب على العمل القليل بالكثير من الثواب."},
    {"name": "العلي", "meaning": "الرفيع القدر الذي لا رتبة فوق رتبته."},
    {"name": "الكبير", "meaning": "العظيم الشأن الذي كل شيء دونه."},
    {"name": "الحفيظ", "meaning": "الذي يحفظ عباده وأعمالهم من الضياع."},
    {"name": "الكريم", "meaning": "الكثير الخير، الجواد المعطي الذي لا ينفد عطاؤه."},
    {"name": "المجيب", "meaning": "الذي يجيب دعاء من دعاه."},
    {"name": "الواسع", "meaning": "الذي وسع رزقه جميع خلقه، ووسعت رحمته كل شيء."},
    {"name": "الحكيم", "meaning": "المُحكم في تدبيره، والذي يضع الأشياء في مواضعها."},
    {"name": "الودود", "meaning": "المُحب لعباده الصالحين، والمحبوب في قلوب أوليائه."}
]

TASBEEH_AZKAR = [
    {"text": "سُبْحَانَ اللهِ", "target": 33},
    {"text": "الْحَمْدُ للهِ", "target": 33},
    {"text": "اللهُ أَكْبَرُ", "target": 33},
]

MORNING_AZKAR = [
    "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لاَ إِلَهَ إِلاَّ اللَّهُ وَحْدَهُ لاَ شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.",
    "اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ.",
]

EVENING_AZKAR = [
    "أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لاَ إِلَهَ إِلاَّ اللَّهُ وَحْدَهُ لاَ شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.",
    "اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ.",
]

ARABIC_TO_ENGLISH_CITIES = {
    "بغداد": "Baghdad", "البصرة": "Basra", "الموصل": "Mosul",
    "أربيل": "Erbil", "اربيل": "Erbil", "هولير": "Erbil",
    "الرمادي": "Ramadi", "الفلوجة": "Fallujah",
    "كربلاء": "Karbala", "النجف": "Najaf",
    "كركوك": "Kirkuk", "السليمانية": "Sulaymaniyah",
    "دهوك": "Dohuk", "الناصرية": "Nasiriyah",
    "الحلة": "Hillah", "العمارة": "Amarah", "الديوانية": "Diwaniyah",
}

@client.on(events.NewMessage(pattern="^سيرة النبي$"))
async def seerah_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    text = "**صلى الله على محمد ﷺ**\n\n**اختر مرحلة من السيرة النبوية الشريفة لعرضها:**"
    buttons = []
    for key, value in SEERAH_STAGES.items():
        buttons.append([Button.inline(value["button"], data=f"seerah:{key}")])
    await event.reply(text, buttons=buttons)

@client.on(events.NewMessage(pattern="^اسماء الله الحسنى$"))
async def asma_al_husna_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    random_name = random.choice(NAMES_OF_ALLAH)
    text = f"**✨ {random_name['name']} ✨**\n\n**المعنى:**\n**{random_name['meaning']}**"
    buttons = [
        [Button.inline("💎 اسم آخر", data="asma_husna:random")],
        [Button.inline("📋 عرض القائمة كاملة", data="asma_husna:full_list")]
    ]
    await event.reply(text, buttons=buttons)

@client.on(events.NewMessage(pattern="^سبحة$"))
async def start_tasbeeh_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    zikr_info = TASBEEH_AZKAR[0]
    zikr_text = zikr_info["text"]
    zikr_target = zikr_info["target"]
    
    message_text = f"**الهدف: {zikr_target}**"
    
    buttons = [
        [
            Button.inline(
                f"{zikr_text} [0]", 
                data=f"tasbeeh:click:{zikr_text}:{zikr_target}:0"
            )
        ],
        [
            Button.inline(
                "🔄 إعادة التصفير", 
                data=f"tasbeeh:reset:{zikr_text}:{zikr_target}:0"
            )
        ]
    ]
    await event.reply(message_text, buttons=buttons)

@client.on(events.NewMessage(pattern="^اذكار الصباح$"))
async def morning_azkar_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    zikr = random.choice(MORNING_AZKAR)
    await event.reply(f"**☀️ من أذكار الصباح ☀️**\n\n**- {zikr}**")

@client.on(events.NewMessage(pattern="^اذكار المساء$"))
async def evening_azkar_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    zikr = random.choice(EVENING_AZKAR)
    await event.reply(f"**🌙 من أذكار المساء 🌙**\n\n**- {zikr}**")

@client.on(events.NewMessage(pattern=r"^اذان (.+)"))
async def prayer_times_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    city_arabic = event.pattern_match.group(1).strip()
    city_english = ARABIC_TO_ENGLISH_CITIES.get(city_arabic)
    if not city_english:
        return await event.reply(f"**عذراً، المدينة '{city_arabic}' غير موجودة في القائمة عندي أو كتبتها غلط.\nجرب مدينة عراقية رئيسية.**")
    api_url = f"https://api.aladhan.com/v1/timingsByCity"
    params = {"city": city_english, "country": "Iraq", "method": 4}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json().get("data")
        if data:
            timings = data.get("timings")
            date_hijri = data.get("date", {}).get("hijri", {}).get("date")
            date_gregorian = data.get("date", {}).get("gregorian", {}).get("date")
            prayer_times_text = (
                f"**🕌 مواقيت الصلاة لمدينة {city_english}**\n**📅 {date_gregorian} | {date_hijri}**\n\n"
                f"**الفجر:** {timings['Fajr']}\n**الشروق:** {timings['Sunrise']}\n"
                f"**الظهر:** {timings['Dhuhr']}\n**العصر:** {timings['Asr']}\n"
                f"**المغرب:** {timings['Maghrib']}\n**العشاء:** {timings['Isha']}"
            )
            await event.reply(prayer_times_text)
        else:
             await event.reply("**ما لگيت بيانات لهاي المدينة من المصدر.**")
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response:
            await event.reply(f"**الموقع رفض الطلب للمدينة '{city_english}'.\nكود الخطأ: {e.response.status_code}**")
        else:
            await event.reply(f"**صارت مشكلة وما گدرت أجيب مواقيت الصلاة.\n`{e}`**")
    except Exception as e:
        await event.reply(f"**صارت مشكلة وما گدرت أجيب مواقيت الصلاة.\n`{e}`**")

@client.on(events.NewMessage(pattern="^حديث$"))
async def hadith_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return
    
    random_hadith = random.choice(HADITH_LIST)
    await event.reply(f"**قال رسول الله ﷺ:**\n\n\"{random_hadith}\"")

@client.on(events.NewMessage(pattern="^حصن المسلم$"))
async def hisn_almuslim_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return
    
    text = "**حصن المسلم**\n\n**اختر الدعاء الذي تريد عرضه:**"
    buttons = []
    for key, value in HISN_ALMUSLIM.items():
        buttons.append([Button.inline(value["button"], data=f"hisn:{key}")])
    
    await event.reply(text, buttons=buttons)
