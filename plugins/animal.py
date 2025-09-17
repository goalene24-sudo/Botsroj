# plugins/animal.py
import random
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from bot import client
from .utils import check_activation

# --- ID المطور ---
DEVELOPER_ID = 196351880

# --- (تم التعديل) إعادة هيكلة البيانات لربط كل حيوان بفيديو وأوصاف خاصة به ---
ANIMAL_DATA = [
    {
        "video": "https://graph.org/file/720a8d292301289bb7ca4.mp4",
        "name": "المطي 🦓",
        "descriptions": ["زربه", "الأصلي", "عنيد", "مال شغل"]
    },
    {
        "video": "https://graph.org/file/fa43723297d16ebccfa94.mp4",
        "name": "الكلب 🐕‍🦺",
        "descriptions": ["مال شوارع", "الأليف", "الوفي", "سعران"]
    },
    {
        "video": "https://graph.org/file/bc4c35ca805ab9e4ef8d7.mp4",
        "name": "القرد 🐒",
        "descriptions": ["لزكـه", "يقفز", "يأكل موز", "مشهور"]
    },
    {
        "video": "https://graph.org/file/7cc42816b3e161f7183b6.mp4",
        "name": "الصخل 🐐",
        "descriptions": ["محترم", "جبلي", "عنيد", "صوته عالي"]
    },
    {
        "video": "https://graph.org/file/8beaf555e0d4e3f00c294.mp4",
        "name": "الطلي 🐑",
        "descriptions": ["ابو البعرور", "الوصخ", "الأليف", "مال عيد"]
    },
    {
        "video": "https://graph.org/file/c34cb870037a4ed2be972.mp4",
        "name": "البزون 🐈",
        "descriptions": ["ابوخالد", "المنزلي", "الكيوت", "يخرمش"]
    },
    {
        "video": "https://graph.org/file/c499feb6a51dea16a1fe5.mp4",
        "name": "أبو بريص 🦎",
        "descriptions": ["الزاحف", "السريع", "المقرف", "يغير لونه"]
    },
    {
        "video": "https://graph.org/file/19b193f06d680e3ec79c0.mp4",
        "name": "الجريذي 🐀",
        "descriptions": ["ابو المجاري", "الجبان", "سريع الحركة", "يأكل كل شيء"]
    },
    {
        "video": "https://graph.org/file/cd1fcb86af78d83ba9002.mp4",
        "name": "الهايشه 🐄",
        "descriptions": ["الحلوبة", "السمينة", "البطيئة", "أم خوار"]
    }
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
        
    if user.id == DEVELOPER_ID:
        await event.reply("**دي . . انـهُ المطـور . . انتـه الحيـوان ولك**")
        return

    zed = await event.reply("`جاري الكشف...`")

    try:
        photos = await client(GetUserPhotosRequest(user_id=user.id, offset=0, max_id=0, limit=100))
        photo_count = photos.count
        if photo_count == 0:
            photo_status = "لا توجد صور"
        else:
            photo_status = f"{photo_count} صور"
    except Exception:
        photo_status = "غير معروف" 
        
    # --- (تم التعديل) اختيار حزمة الحيوان بالكامل ---
    animal_pack = random.choice(ANIMAL_DATA)
    video_url = animal_pack["video"]
    base_name = animal_pack["name"]
    description = random.choice(animal_pack["descriptions"])
    
    # دمج الاسم مع الوصف
    animal_full_name = f"{base_name} {description}"
    
    percentage = random.choice(PERCENTAGES)
    username = f"@{user.username}" if user.username else "لا يوجد معرف"

    caption = (
        f"**╮•🦦 الحيوان ⇦** {user.first_name}\n"
        f"**ٴ╼──────────────────╾**\n"
        f"**• 🌚 | معـرفه  ⇦** {username}\n"
        f"**• 🌚 | ايـديه   ⇦** `{user.id}`\n"
        f"**• 🌚 | صـوره  ⇦** `{photo_status}`\n"
        f"**• 🌚 | نــوعه   ⇦** {animal_full_name}\n"
        f"**• 🌚 | نسبتـه  ⇦** **{percentage}**\n"
    )

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
