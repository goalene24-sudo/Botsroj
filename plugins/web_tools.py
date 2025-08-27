# plugins/web_tools.py
import httpx
import wikipedia
import random
import asyncio
from telethon import events
# (تمت الإضافة) سنحتاج هذا لمعالجة الأخطاء
from telethon.errors.rpcerrorlist import YouBlockedUserError
from bot import client
from .utils import check_activation
from googletrans import Translator, LANGUAGES
from .slang_data import IRAQI_SLANG
from .zakhrafa_data import ZAKHRAFA_STYLES

# --- قواميس مساعدة ---
WEATHER_TRANSLATIONS = {
    "Clear": "صحو ☀️", "Sunny": "مشمس ☀️", "Partly cloudy": "غائم جزئياً 🌤️",
    "Cloudy": "غائم ☁️", "Overcast": "ملبد بالغيوم 🌥️", "Mist": "ضباب خفيف 🌫️",
    "Patchy rain possible": "احتمال أمطار خفيفة متفرقة 🌦️", "Fog": "ضباب 🌫️",
    "Light rain": "مطر خفيف 🌧️", "Heavy rain": "مطر غزير 🌧️",
    "Thundery outbreaks possible": "احتمال عواصف رعدية ⛈️",
}

@client.on(events.NewMessage(pattern=r"^طقس(?: (.+))?$"))
async def weather_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    city = event.pattern_match.group(1)
    if not city:
        return await event.reply("**وين الطقس؟ لازم تكتب اسم المدينة.\nمثال: `طقس بغداد`**")
    api_url = f"https://wttr.in/{city.strip()}?format=j1"
    headers = {"Accept-Language": "ar"}
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        current_condition = data['current_condition'][0]
        nearest_area = data['nearest_area'][0]
        city_name = nearest_area['areaName'][0]['value']
        country_name = nearest_area['country'][0]['value']
        temp_c, feels_like_c, humidity = current_condition['temp_C'], current_condition['FeelsLikeC'], current_condition['humidity']
        weather_desc_en, wind_speed_kmph = current_condition['weatherDesc'][0]['value'], current_condition['windspeedKmph']
        weather_desc_ar = WEATHER_TRANSLATIONS.get(weather_desc_en, weather_desc_en)
        weather_text = (
            f"**حالة الطقس في {city_name}, {country_name} 📍**\n\n"
            f"**الحالة:** {weather_desc_ar}\n**درجة الحرارة:** {temp_c}° مئوية\n"
            f"**الإحساس الفعلي:** {feels_like_c}° مئوية\n**الرطوبة:** {humidity}%\n"
            f"**سرعة الرياح:** {wind_speed_kmph} كم/ساعة"
        )
        await event.reply(weather_text)
    except httpx.HTTPError:
        await event.reply(f"**ما لگيت مدينة بهذا الاسم '{city}'، تأكد من كتابتها صح.**")
    except Exception as e:
        await event.reply(f"**صارت مشكلة وما گدرت أجيب حالة الطقس.\n`{e}`**")

@client.on(events.NewMessage(pattern=r"^ترجم(?: ([a-zA-Z]{2,5}))?(?: (.*))?s*$"))
async def translate_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    args = event.pattern_match.groups()
    target_lang, text_to_translate = args[0], args[1]
    reply_msg = await event.get_reply_message()
    if not text_to_translate and reply_msg:
        text_to_translate = reply_msg.text
    if not text_to_translate:
        return await event.reply(
            "**شترجم؟ لازم ترد على رسالة أو تكتب النص ويه الأمر.**\n"
            "**مثال (بالرد):** `ترجم en`\n"
            "**مثال (مباشر):** `ترجم ar Hello world`"
        )
    if not target_lang: target_lang = 'ar'
    if target_lang not in LANGUAGES:
        return await event.reply(f"**ما أعرف هاي اللغة '{target_lang}'. اكتب رمز صحيح مثل `en` أو `ar`.**")
    loading_msg = await event.reply("**لحظة، دا اترجم... 🌍**")
    try:
        translator = Translator()
        result = translator.translate(text_to_translate, dest=target_lang)
        src_lang = LANGUAGES.get(result.src, result.src).capitalize()
        dest_lang = LANGUAGES.get(result.dest, result.dest).capitalize()
        response_text = (
            f"**✅ تمت الترجمة بنجاح**\n\n"
            f"**من اللغة:** {src_lang}\n"
            f"**إلى اللغة:** {dest_lang}\n\n"
            f"**النص المترجم:**\n`{result.text}`"
        )
        await loading_msg.edit(response_text)
    except Exception as e:
        await loading_msg.edit(f"**صارت مشكلة وما گدرت أترجم.\n`{e}`**")

@client.on(events.NewMessage(pattern=r"^ويكي(?: (.*))?$"))
async def wiki_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    search_term = event.pattern_match.group(1)
    if not search_term:
        return await event.reply("**شنو تبحث عنه؟ لازم تكتب شي ويه الأمر.\nمثال: `ويكي العراق`**")
    loading_msg = await event.reply("**لحظة، دا أدورلك بالموسوعة... 🧐**")
    try:
        wikipedia.set_lang("ar")
        page = wikipedia.page(search_term, auto_suggest=True)
        summary = wikipedia.summary(search_term, sentences=5)
        result_text = (
            f"**📖 | نتيجة البحث عن: {page.title}**\n\n"
            f"**{summary}...**\n\n"
            f"**[قراءة المزيد على ويكيبيديا]({page.url})**"
        )
        await loading_msg.edit(result_text, link_preview=False)
    except wikipedia.exceptions.PageError:
        await loading_msg.edit(f"**عذراً، ما لگيت أي صفحة بهذا الاسم: '{search_term}'.\nتأكد من كتابته صح.**")
    except wikipedia.exceptions.DisambiguationError as e:
        options_text = "\n".join(f"- `{opt}`" for opt in e.options[:5])
        await loading_msg.edit(f"**لگيت أكثر من نتيجة محتملة. يا هي تقصد؟\n\n{options_text}**")
    except Exception as e:
        await loading_msg.edit(f"**صارت مشكلة وما گدرت أبحث.\n`{e}`**")

@client.on(events.NewMessage(pattern=r"^احسب (.+)"))
async def calculate_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    expression = event.pattern_match.group(1).strip()
    if not expression:
        return await event.reply("**شحسب؟ اكتب عملية حسابية ويه الأمر.**\n**مثال: `احسب 5 * 10`**")
    api_url = "http://api.mathjs.org/v4/"
    params = {"expr": expression}
    loading_msg = await event.reply("🤔 **جاري الحساب...**")
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(api_url, params=params)
        if response.status_code == 200:
            result = response.text
            await loading_msg.edit(f"**🔢 النتيجة: `{result}`**")
        else:
            error_message = response.text
            await loading_msg.edit(f"**❌ خطأ في العملية الحسابية:**\n`{error_message}`")
    except httpx.HTTPError as e:
        await loading_msg.edit(f"**ما گدرت أتصل بخدمة الحسابات.\n`{e}`**")
    except Exception as e:
        await loading_msg.edit(f"**صارت مشكلة وما گدرت أحسب.\n`{e}`**")

# --- (تم التعديل) النسخة النهائية لأمر "معنى" باستخدام بوت مساعد ---
@client.on(events.NewMessage(pattern=r"^معنى (.+)"))
async def define_handler(event):
    if not await check_activation(event.chat_id): return

    word = event.pattern_match.group(1).strip()
    if not word:
        return await event.reply("**شنو الكلمة اللي تريد تعرف معناها؟**\n**مثال: `معنى استكان`**")

    # الخطوة 1: البحث في القاموس المحلي أولاً
    if word.lower() in IRAQI_SLANG:
        definition = IRAQI_SLANG[word.lower()]
        return await event.reply(f"**📖 | معنى كلمة: {word} (لهجة عراقية)**\n\n{definition}")

    loading_msg = await event.reply(f"**📖 لحظات... دا أدور على معنى كلمة '{word}'...**")
    
    # الخطوة 2: استخدام البوت المساعد @zzznambot
    proxy_bot = "@zzznambot"
    try:
        async with client.conversation(proxy_bot, timeout=20) as conv:
            # إرسال الكلمة للبوت المساعد
            await conv.send_message(word)
            
            # انتظار الرد منه تحديداً (معرف البوت هو 2045033062)
            response = await conv.get_response(from_users=2045033062)
            
            # التحقق إذا لم يجد البوت المساعد الكلمة
            if "لا يوجد معنى" in response.text or "can't find that" in response.text:
                await loading_msg.edit(f"**عذراً، لم يتم العثور على تعريف للكلمة '{word}'.**")
            else:
                # نجح الأمر! نحذف رسالة التحميل ونرسل رده
                await loading_msg.delete()
                # نرسل رسالة البوت المساعد كما هي للحفاظ على التنسيق
                await event.reply(response.message)
                
    except YouBlockedUserError:
        await loading_msg.edit("**⚠️ | خطأ: يجب إلغاء حظر البوت المساعد @zzznambot لتتمكن من استخدام هذا الأمر.**")
    except asyncio.TimeoutError:
        await loading_msg.edit("**⌛️ | استغرق البوت المساعد وقتاً طويلاً للرد. يرجى المحاولة مرة أخرى.**")
    except Exception as e:
        print(f"Error in define_handler (proxy bot): {e}")
        await loading_msg.edit("**حدث خطأ غير متوقع أثناء التواصل مع البوت المساعد.**")


@client.on(events.NewMessage(pattern=r"^زخرف (.+)"))
async def zakhrafa_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    text_to_decorate = event.pattern_match.group(1).strip()
    if not text_to_decorate:
        return await event.reply("**اكتب نصاً بعد الأمر لزخرفته.**")

    decorated_results = [f"**🎨 | زخرفة النص:** `{text_to_decorate}`\n"]
    
    words = text_to_decorate.split()
    stretched_words = ["ـ".join(list(word)) for word in words]
    stretched_text = " ".join(stretched_words)
    decorated_results.append(f"▫️ `{stretched_text}`")

    for style in ZAKHRAFA_STYLES:
        decorated_text = ""
        style_type = style.get("type")

        if style_type == "map":
            char_map = style.get("data", {})
            for char in text_to_decorate:
                decorated_text += char_map.get(char, char)
            decorated_results.append(f"▫️ `{decorated_text}`")

        elif style_type == "prefix_suffix":
            prefix = style.get("prefix", "")
            suffix = style.get("suffix", "")
            decorated_text = f'{prefix}{text_to_decorate}{suffix}'
            decorated_results.append(f"▫️ `{decorated_text}`")
    
    final_message = "\n".join(decorated_results)
    await event.reply(final_message)
