# plugins/animal.py
import random
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from bot import client
from .utils import check_activation

# --- (تم التعديل) إضافة ID المطور ---
DEVELOPER_ID = 196351880

# --- (تم التعديل والتوسع) قائمة الحيوانات مع أسماء عامة فقط ---
ANIMAL_DATA = {
    1: {"video": "https://graph.org/file/720a8d292301289bb7ca4.mp4", "base_name": "المطي"},
    2: {"video": "https://graph.org/file/fa43723297d16ebccfa94.mp4", "base_name": "الكلب"},
    3: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "base_name": "القرد"},
    4: {"video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4", "base_name": "الصخل"},
    5: {"video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4", "base_name": "الطلي"},
    6: {"video": "https://graph.org/file/c34cb870037a4ed2be972.mp4", "base_name": "البزون"},
    7: {"video": "https://graph.org/file/c499feb6a51dea16a1fe5.mp4", "base_name": "أبو بريص"},
    8: {"video": "https://graph.org/file/19b193f06d680e3ec79c0.mp4", "base_name": "الجريذي"},
    9: {"video": "https://graph.org/file/cd1fcb86af78d83ba9002.mp4", "base_name": "الهايشة"},
    10: {"video": "https://graph.org/file/720a8d292301289bb7ca4.mp4", "base_name": "الثعلب"},
    11: {"video": "https://graph.org/file/fa43723297d16ebccfa94.mp4", "base_name": "الذيب"},
    12: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "base_name": "التمساح"},
    13: {"video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4", "base_name": "الضفدع"},
    14: {"video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4", "base_name": "الصقر"},
    15: {"video": "https://graph.org/file/c34cb870037a4ed2be972.mp4", "base_name": "العقرب"},
    16: {"video": "https://graph.org/file/720a8d292301289bb7ca4.mp4", "base_name": "الديك"},
    17: {"video": "https://graph.org/file/fa43723297d16ebccfa94.mp4", "base_name": "الحمار"},
    18: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "base_name": "الفأر"},
    19: {"video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4", "base_name": "الخنزير"},
    20: {"video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4", "base_name": "البومة"},
    21: {"video": "https://graph.org/file/c34cb870037a4ed2be972.mp4", "base_name": "البطريق"},
    22: {"video": "https://graph.org/file/c499feb6a51dea16a1fe5.mp4", "base_name": "الأرنب"},
    23: {"video": "https://graph.org/file/19b193f06d680e3ec79c0.mp4", "base_name": "السلحفاة"},
    24: {"video": "https://graph.org/file/cd1fcb86af78d83ba9002.mp4", "base_name": "الكوالا"},
    25: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "base_name": "البغل"},
    26: {"video": "https://graph.org/file/720a8d292301289bb7ca4.mp4", "base_name": "النسر"},
    27: {"video": "https://graph.org/file/fa43723297d16ebccfa94.mp4", "base_name": "الوطواط"},
    28: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "base_name": "السمكة"},
    29: {"video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4", "base_name": "الأفعى"},
    30: {"video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4", "base_name": "الجرادة"},
}

# --- (جديد) قائمة الأوصاف الفكاهية للحيوانات ---
ANIMAL_DESCRIPTIONS = [
    "زربه 🦓",
    "شوارع 🐕‍🦺",
    "لزكـه 🐒",
    "محترم 🐐",
    "ابو البعرور الوصخ 🐑",
    "ابوخالد 🐈",
    "الزاحف 🦎",
    "ابو المجاري 🐀",
    "خرسه 🐄",
    "مكار 🦊",
    "عاوي 🐺",
    "دمعته تكت 🐊",
    "لزكه 🐸",
    "كاسر 🦅",
    "سام 🦂",
    "صياح 🐔",
    "وگح 🐴",
    "جبان 🐁",
    "وصخ 🐗",
    "خرسه 🦉",
    "متجمد 🐧",
    "خايف 🐇",
    "بطيئة 🐢",
    "نعسان 🐨",
    "عنيد 🐴",
    "شرس 🦅",
    "طائر ليلي 🦉",
    "بطيء الحركة 🐌",
    "بارد الدم 🐍",
    "مؤذي 🐛",
    "متخلف 🐒",
    "غبي 🐑",
    "قبيح 🐗",
    "لزكه 🦎",
    "حقير 🐀",
    "صوت عالي 🐔",
    "كسول 🐨",
    "جبان 🐇",
    "متخبي 🐸",
    "غادر 🐺",
    "اناني 🦊",
    "متسخ 💩",
    "فاشل 👎",
    "نذل 🐍",
    "لئيم 🦂",
    "عديم الفائدة 🗑️",
    "مثير للشفقة 🥺"
]


PERCENTAGES = [
    "100% مو حيوان غنبله 😱😂.",
    "90% مو حيوان ضيم 😱😂👆",
    "80% 😱😂",
    "70% 😱😂",
    "60% براسه 60 حظ 👌😂",
    "50% حيوان هجين👍😂",
    "40% خوش حيوان 👌😂",
    "30% 😒😂",
    "20% 😒😂",
    "10% 😒😂",
    "0% 😢😂",
]

@client.on(events.NewMessage(pattern="^كشف حيوان$"))
async def who_is_animal(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    reply_message = await event.get_reply_message()
    if not reply_message:
        await event.reply("**لازم تسوي رپلَي على واحد حتى أكشفه.**")
        return

    user = await reply_message.get_sender()
    if not user:
        await event.reply("**ما گدرت أعرف هذا المستخدم.**")
        return
        
    # --- (تم التعديل) إضافة حماية المطور ---
    if user.id == DEVELOPER_ID:
        await event.reply("**دي . . انـهُ المطـور . . انتـه الحيـوان ولك**")
        return

    # رسالة الانتظار
    zed = await event.reply("`جاري الكشف...`")

    # جلب عدد صور البروفايل
    try:
        photos = await client(GetUserPhotosRequest(user_id=user.id, offset=0, max_id=0, limit=100))
        photo_count = photos.count
        if photo_count == 0:
            photo_status = "لا توجد صور"
        else:
            photo_status = f"{photo_count} صور"
    except Exception:
        photo_status = "غير معروف" 
        
    # اختيار حيوان عشوائي
    animal_choice_data = random.choice(list(ANIMAL_DATA.values()))
    video_url = animal_choice_data["video"]
    base_animal_name = animal_choice_data["base_name"] # اسم الحيوان الأساسي

    # اختيار وصف فكاهي عشوائي ونسبة عشوائية
    random_description = random.choice(ANIMAL_DESCRIPTIONS)
    percentage = random.choice(PERCENTAGES)
    
    # دمج الاسم الأساسي مع الوصف الفكاهي
    animal_full_name = f"{base_animal_name} {random_description}"

    username = f"@{user.username}" if user.username else "لا يوجد معرف"

    # بناء الرسالة
    caption = (
        f"**╮•🦦 الحيوان ⇦** {user.first_name}\n"
        f"**ٴ╼──────────────────╾**\n"
        f"**• 🌚 | معـرفه  ⇦** {username}\n"
        f"**• 🌚 | ايـديه   ⇦** `{user.id}`\n"
        f"**• 🌚 | صـوره  ⇦** `{photo_status}`\n"
        f"**• 🌚 | نــوعه   ⇦** {animal_full_name}\n" # تم تحديث هذا السطر
        f"**• 🌚 | نسبتـه  ⇦** **{percentage}**\n"
    )

    # إرسال الفيديو مع الرسالة وحذف رسالة الانتظار
    try:
        await client.send_file(
            event.chat_id,
            file=video_url,
            caption=caption,
            reply_to=reply_message
        )
        await zed.delete()
    except Exception as e:
        await zed.edit(f"**عذرًا، حدث خطأ:**\n`{e}`")
