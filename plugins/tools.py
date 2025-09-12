import os
import pytz
import json
from gtts import gTTS
from datetime import datetime
from telethon import events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from sqlalchemy.future import select

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import GlobalSetting, User
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation
from .admin import get_or_create_chat

# --- قواميس مساعدة ---
TIMEZONE_MAP = {
    "بغداد": "Asia/Baghdad", "لندن": "Europe/London", "نيويورك": "America/New_York",
    "طوكيو": "Asia/Tokyo", "القاهرة": "Africa/Cairo", "دبي": "Asia/Dubai",
    "موسكو": "Europe/Moscow", "الرياض": "Asia/Riyadh", "باريس": "Europe/Paris",
    "برلين": "Europe/Berlin", "اسطنبول": "Europe/Istanbul", "بيروت": "Asia/Beirut",
    "الدوحة": "Asia/Qatar", "الكويت": "Asia/Kuwait",
    "baghdad": "Asia/Baghdad", "london": "Europe/London", "new york": "America/New_York",
    "tokyo": "Asia/Tokyo", "cairo": "Africa/Cairo", "dubai": "Asia/Dubai",
    "moscow": "Europe/Moscow", "riyadh": "Asia/Riyadh", "paris": "Europe/Paris",
    "berlin": "Europe/Berlin", "istanbul": "Europe/Istanbul", "beirut": "Asia/Beirut",
    "doha": "Asia/Qatar", "kuwait": "Asia/Kuwait",
}

DAYS_AR = {
    "Saturday": "السبت", "Sunday": "الأحد", "Monday": "الاثنين",
    "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", "Thursday": "الخميس",
    "Friday": "الجمعة"
}

# --- دالة مساعدة للتحقق من الأوامر المعطلة عالميًا ---
async def is_globally_disabled(command_name):
    """التحقق إذا كان الأمر معطلاً على مستوى البوت."""
    async with AsyncDBSession() as session:
        result = await session.execute(
            select(GlobalSetting).where(GlobalSetting.key == "disabled_cmds")
        )
        setting = result.scalar_one_or_none()
        if setting and setting.value:
            try:
                disabled_list = json.loads(setting.value)
                return command_name in disabled_list
            except json.JSONDecodeError:
                return False
        return False

@client.on(events.NewMessage(pattern="^معلومات المجموعة$"))
async def group_info_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("معلومات المجموعة"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    chat = await event.get_chat()
    loading_msg = await event.reply("**جاي أحسب... 🤓**")
    
    try:
        members_count = (await client.get_participants(event.chat_id, limit=0)).total
        admins = await client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)
        admins_count = len(admins)
        
        async with AsyncDBSession() as session:
            chat_obj = await get_or_create_chat(session, event.chat_id)
            total_msgs = chat_obj.total_msgs
            
        info_text = (
            f"**📊 هاي شنو وضع مجموعتكم... خل نشوف:**\n\n"
            f"**الاسم:** {chat.title}\n**الآيدي:** `{event.chat_id}`\n"
            f"**الأعضاء:** عدكم `{members_count}` نفر، هوووسة!\n"
            f"**المشرفين:** `{admins_count}` مدير يديرون الهوسة.\n"
            f"**الحچي:** سولفتوا لحد هسه `{total_msgs}` رسالة... لسانكم شطوله! 👅\n\n"
            f"**عاشت ايدكم استمروا باللغط! 😂**"
        )
        await loading_msg.edit(info_text)
    except Exception as e:
        await loading_msg.edit(f"**ما گدرت أجيب المعلومات، صارت مشكلة:\n`{e}`**")

@client.on(events.NewMessage(pattern="^احصائيات$"))
async def group_stats_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("احصائيات"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")

    async with AsyncDBSession() as session:
        result = await session.execute(
            select(User)
            .where(User.chat_id == event.chat_id)
            .order_by(User.msg_count.desc())
            .limit(1)
        )
        most_active_user_obj = result.scalar_one_or_none()

    if not most_active_user_obj or most_active_user_obj.msg_count == 0:
        return await event.reply("**ماكو احصائيات بعد، المجموعة جديدة لو محد يسولف؟ 🤔**")

    max_msgs = most_active_user_obj.msg_count
    most_active_id = most_active_user_obj.user_id
    
    try:
        user = await client.get_entity(most_active_id)
        stats_text = (
            f"**🏆 نجم المجموعة (الأكثر حچياً):**\n\n"
            f"**هو البطل [{user.first_name}](tg://user?id={user.id})! 👑**\n"
            f"**عدد رسائله:** `{max_msgs}` **رسالة.**\n\n"
            f"**هذا لسان لو مايكروفون؟ سكتة ماكو! 🎤😂**"
        )
        await event.reply(stats_text)
    except Exception as e:
        await event.reply(f"**ما لگيت معلومات عن أكثر واحد فعال، يمكن غادر المجموعة.\n`{e}`**")

@client.on(events.NewMessage(pattern=r"^احجي(?: (.*))?$"))
async def tts_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("احجي"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")

    text_to_say = event.pattern_match.group(1)
    if not text_to_say:
        return await event.reply("**شحچي؟ لازم تكتبلي كلام.\nمثال: `احجي صباح الخير`**")
        
    loading_msg = await event.reply("**لحظة دا أسجل البصمة... 🎙️**")
    file_name = f"voice_{event.id}.ogg"
    try:
        tts = gTTS(text=text_to_say, lang='ar')
        tts.save(file_name)
        await client.send_file(
            event.chat_id, file_name, voice_note=True, reply_to=event.id
        )
        await loading_msg.delete()
    except Exception as e:
        await loading_msg.edit(f"**ما گدرت أحچي، صارت مشكلة:\n`{e}`**")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

@client.on(events.NewMessage(pattern=r"^وقت(?: (.*))?$"))
async def world_clock_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("وقت"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    city_name_raw = event.pattern_match.group(1)
    if not city_name_raw:
        return await event.reply("**لمعرفة الوقت، اكتب اسم مدينة رئيسية.\nمثال: `وقت لندن`**")
    
    city_name = city_name_raw.strip().lower()
    timezone_str = TIMEZONE_MAP.get(city_name)
    
    if not timezone_str:
        return await event.reply(f"**عذراً، المدينة '{city_name_raw}' غير مدعومة حالياً. جرب مدينة رئيسية أخرى.**")

    try:
        timezone = pytz.timezone(timezone_str)
        now_in_timezone = datetime.now(timezone)
        
        time_str = now_in_timezone.strftime("%I:%M:%S %p").replace("AM", "صباحاً").replace("PM", "مساءً")
        date_str = now_in_timezone.strftime("%Y-%m-%d")
        day_en = now_in_timezone.strftime("%A")
        day_ar = DAYS_AR.get(day_en, day_en)
        
        result_text = (
            f"**الوقت الحالي في {city_name_raw.title()} هو:**\n\n"
            f"**🕒 الساعة:** {time_str}\n"
            f"**🗓️ التاريخ:** {date_str} **(يوم {day_ar})**\n\n"
            f"**المنطقة الزمنية:** `{timezone_str}`"
        )
        await event.reply(result_text)
    except Exception as e:
        await event.reply(f"**صارت مشكلة وما گدرت أجيب الوقت.\n`{e}`**")


@client.on(events.NewMessage(pattern=r"^عمري (.+)"))
async def age_calculator_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("عمري"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    date_str = event.pattern_match.group(1)
    try:
        birth_date = None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
            try:
                birth_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if birth_date is None:
            raise ValueError("Invalid date format")

        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        next_birthday = birth_date.replace(year=today.year)
        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)
            
        days_until_birthday = (next_birthday - today).days

        result_text = (
            f"**📅 حساب العمر:**\n\n"
            f"**🔹 عمرك الحالي هو:** `{age}` **سنة.**\n"
            f"**🔹 عيد ميلادك الجاي بعد:** `{days_until_birthday}` **يوم!** 🎂"
        )
        await event.reply(result_text)

    except ValueError:
        await event.reply(
            "**الصيغة غلط! ❌**\n"
            "**لازم تكتب تاريخ ميلادك بهاي الطريقة (يوم-شهر-سنة).**\n"
            "**مثال:** `عمري 25-12-1999`"
        )
    except Exception as e:
        await event.reply(f"**صارت مشكلة وما گدرت أحسب عمرك.\n`{e}`**")


@client.on(events.NewMessage(pattern=r"^المطور$"))
async def developer_info_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if await is_globally_disabled("المطور"):
        return await event.reply("**(هذا الامر تحت الصيانه حاليا تواصل مع المطور اذا ارد شيئا @tit_50)**")
        
    DEV_USER_ID = 196351880 # معرف المطور
    dev_name = "وِهےـِمِے"
    dev_user = "@tit_50"
    dev_bio = "أڪبـر عِبـارة مُـريحـة مـا أحـزن اللـه عبـداً إِلا ليُـسعـدﮪ💙"
    dev_button_text = "𝓜𝓨 𝓟𝓡𝓞𝓕𝓘𝓛𝓔"
    dev_button_url = "https://t.me/tit_50"
    
    caption_text = f"""- 𝖒𝖆𝖎𝖓 𝖉𝖊𝖛𝖊𝖑𝖔𝖕𝖊𝖗 𝖎𝖓𝖋𝖔𝖗𝖒𝖆𝖙𝖎𝖔𝖓 :

🔹 ⋄ 𝖓𝖆𝖒𝖊 : {dev_name}
🔹 ⋄ 𝖚𝖘𝖊𝖗 : {dev_user}
🔹 ⋄ 𝖇𝖎𝖔 : {dev_bio}"""
    
    dev_button = Button.url(dev_button_text, dev_button_url)
    
    try:
        dev_photos = await client.get_profile_photos(DEV_USER_ID, limit=1)
        if not dev_photos:
            await event.reply(caption_text, buttons=[[dev_button]])
            return
        
        await event.reply(
            file=dev_photos[0],
            message=caption_text,
            buttons=[[dev_button]]
        )
    except Exception as e:
        await event.reply(f"{caption_text}\n\n⚠️ **تعذر جلب الصورة:** `{e}`", buttons=[[dev_button]])
