# plugins/animal.py
import random
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from bot import client
from .utils import check_activation

# --- (تم التعديل) إضافة ID المطور ---
DEVELOPER_ID = 196351880

# --- (تم التعديل) توسيع قائمة الحيوانات ---
ANIMAL_DATA = {
    1: {"video": "https://graph.org/file/720a8d292301289bb7ca4.mp4", "name": "مطي زربه 🦓"},
    2: {"video": "https://graph.org/file/fa43723297d16ebccfa94.mp4", "name": "جلب شوارع 🐕‍🦺"},
    3: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "name": "قرد لزكـه 🐒"},
    4: {"video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4", "name": "صخل محترم 🐐"},
    5: {"video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4", "name": "طلي ابو البعرور 🐑"},
    6: {"video": "https://graph.org/file/c34cb870037a4ed2be972.mp4", "name": "بزون ابوخالد 🐈"},
    7: {"video": "https://graph.org/file/c499feb6a51dea16a1fe5.mp4", "name": "الزاحف ابو بريص 🦎"},
    8: {"video": "https://graph.org/file/19b193f06d680e3ec79c0.mp4", "name": "جريذي ابو المجاري 🐀"},
    9: {"video": "https://graph.org/file/cd1fcb86af78d83ba9002.mp4", "name": "هايشه 🐄"},
    10: {"video": "https://graph.org/file/720a8d292301289bb7ca4.mp4", "name": "ثعلب مكار 🦊"},
    11: {"video": "https://graph.org/file/fa43723297d16ebccfa94.mp4", "name": "ذيب عاوي 🐺"},
    12: {"video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4", "name": "تمساح دمعته تكت 🐊"},
    13: {"video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4", "name": "ضفدع لزكه 🐸"},
    14: {"video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4", "name": "صقر كاسر 🦅"},
    15: {"video": "https://graph.org/file/c34cb870037a4ed2be972.mp4", "name": "عقرب سام 🦂"}
}

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
    except Exception:
        photo_count = "غير معروف"

    # اختيار حيوان ونسبة عشوائية
    animal_choice = random.choice(list(ANIMAL_DATA.values()))
    percentage = random.choice(PERCENTAGES)
    
    video_url = animal_choice["video"]
    animal_name = animal_choice["name"]
    username = f"@{user.username}" if user.username else "لا يوجد معرف"

    # بناء الرسالة
    caption = (
        f"**╮•🦦 الحيوان ⇦** {user.first_name}\n"
        f"**ٴ╼──────────────────╾**\n"
        f"**• 🌚 | معـرفه  ⇦** {username}\n"
        f"**• 🌚 | ايـديه   ⇦** `{user.id}`\n"
        f"**• 🌚 | صـوره  ⇦** `{photo_count}`\n"
        f"**• 🌚 | نــوعه   ⇦** {animal_name}\n"
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