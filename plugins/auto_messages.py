import asyncio
import random
from sqlalchemy.future import select
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

# استيرادات محلية
from bot import OWNER_ID
from database import AsyncDBSession
from models import Chat

# --- قوائم الرسائل ---

DHIKR_MESSAGES = [
    "سبحان الله",
    "الحمد لله",
    "لا إله إلا الله",
    "الله أكبر",
    "سبحان الله وبحمده",
    "سبحان الله العظيم",
    "أستغفر الله وأتوب إليه",
    "لا حول ولا قوة إلا بالله",
    "اللهم صل على نبينا محمد",
    "حسبي الله لا إله إلا هو عليه توكلت وهو رب العرش العظيم"
]

QUOTES_MESSAGES = [
    "“كن أنت التغيير الذي تريد أن تراه في العالم.” - غاندي",
    "“العقل الذي يفتح لفكرة جديدة لن يعود أبداً إلى حجمه الأصلي.” - ألبرت أينشتاين",
    "“النجاح ليس نهائياً، والفشل ليس قاتلاً: إنما الشجاعة للاستمرار هي التي تهم.” - ونستون تشرشل",
    "“الحياة إما مغامرة جريئة أو لا شيء على الإطلاق.” - هيلين كيلر",
    "“الطريقة الوحيدة للقيام بعمل عظيم هي أن تحب ما تفعله.” - ستيف جوبز",
    "“المستقبل ملك لأولئك الذين يؤمنون بجمال أحلامهم.” - إليانور روزفلت",
    "“لا يهم مدى بطئك طالما أنك لا تتوقف.” - كونفوشيوس"
]

# --- دالة للتحقق من صلاحيات المشرف ---

async def is_admin_or_owner(message: Message) -> bool:
    """يتحقق مما إذا كان المستخدم مشرفًا أو مالكًا للمجموعة أو مطور البوت."""
    if message.from_user.id == OWNER_ID:
        return True
    
    member = await message.chat.get_member(message.from_user.id)
    return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]

# --- أوامر التحكم ---

# أوامر الأذكار
@Client.on_message(filters.command(["تفعيل الاذكار", "enable_dhikr"]) & filters.group)
async def enable_dhikr_command(client: Client, message: Message):
    if not await is_admin_or_owner(message):
        return await message.reply_text("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")

    async with AsyncDBSession() as session:
        chat = await session.get(Chat, message.chat.id)
        if not chat: return

        if chat.dhikr_enabled:
            await message.reply_text("**ميزة الأذكار التلقائية مفعلة بالفعل.**")
        else:
            chat.dhikr_enabled = True
            await session.commit()
            # --- (تم التعديل هنا) ---
            await message.reply_text("**✅ تم تفعيل ميزة الأذكار التلقائية بنجاح.**\n**سيرسل البوت ذكرًا كل ساعة.**")

@Client.on_message(filters.command(["تعطيل الاذكار", "disable_dhikr"]) & filters.group)
async def disable_dhikr_command(client: Client, message: Message):
    if not await is_admin_or_owner(message):
        return await message.reply_text("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")

    async with AsyncDBSession() as session:
        chat = await session.get(Chat, message.chat.id)
        if not chat: return

        if not chat.dhikr_enabled:
            await message.reply_text("**ميزة الأذكار التلقائية معطلة بالفعل.**")
        else:
            chat.dhikr_enabled = False
            await session.commit()
            await message.reply_text("**❌ تم تعطيل ميزة الأذكار التلقائية بنجاح.**")

# أوامر الاقتباسات
@Client.on_message(filters.command(["تفعيل الاقتباسات", "enable_quotes"]) & filters.group)
async def enable_quotes_command(client: Client, message: Message):
    if not await is_admin_or_owner(message):
        return await message.reply_text("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")

    async with AsyncDBSession() as session:
        chat = await session.get(Chat, message.chat.id)
        if not chat: return

        if chat.quotes_enabled:
            await message.reply_text("**ميزة الاقتباسات التلقائية مفعلة بالفعل.**")
        else:
            chat.quotes_enabled = True
            await session.commit()
            await message.reply_text("**✅ تم تفعيل ميزة الاقتباسات التلقائية بنجاح.**\n**سيرسل البوت اقتباسًا كل ساعة.**")

@Client.on_message(filters.command(["تعطيل الاقتباسات", "disable_quotes"]) & filters.group)
async def disable_quotes_command(client: Client, message: Message):
    if not await is_admin_or_owner(message):
        return await message.reply_text("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")

    async with AsyncDBSession() as session:
        chat = await session.get(Chat, message.chat.id)
        if not chat: return

        if not chat.quotes_enabled:
            await message.reply_text("**ميزة الاقتباسات التلقائية معطلة بالفعل.**")
        else:
            chat.quotes_enabled = False
            await session.commit()
            await message.reply_text("**❌ تم تعطيل ميزة الاقتباسات التلقائية بنجاح.**")

# --- المهمة الدورية (Scheduler) ---

async def scheduler_task(client: Client):
    """المهمة الرئيسية التي تعمل في الخلفية لإرسال الرسائل الدورية."""
    print(">> مهمة الرسائل الدورية (الأذكار والاقتباسات) قد بدأت. <<")
    minute_counter = 0

    while True:
        await asyncio.sleep(60)  # الانتظار لمدة دقيقة واحدة
        minute_counter += 1

        # --- (تم التعديل هنا) إرسال الأذكار (كل 60 دقيقة) ---
        if minute_counter % 60 == 0:
            try:
                async with AsyncDBSession() as session:
                    stmt = select(Chat.id).where(Chat.dhikr_enabled == True)
                    result = await session.execute(stmt)
                    chat_ids = result.scalars().all()
                
                if chat_ids:
                    random_dhikr = random.choice(DHIKR_MESSAGES)
                    for chat_id in chat_ids:
                        try:
                            await client.send_message(chat_id, random_dhikr)
                            await asyncio.sleep(0.5)  # تأخير بسيط لتجنب الحظر
                        except Exception as e:
                            print(f"[Scheduler] فشل في إرسال الذكر إلى {chat_id}: {e}")
            except Exception as e:
                print(f"[Scheduler] حدث خطأ في قسم إرسال الأذكار: {e}")

        # --- إرسال الاقتباسات (كل 60 دقيقة) ---
        if minute_counter % 60 == 0:
            try:
                async with AsyncDBSession() as session:
                    stmt = select(Chat.id).where(Chat.quotes_enabled == True)
                    result = await session.execute(stmt)
                    chat_ids = result.scalars().all()

                if chat_ids:
                    random_quote = random.choice(QUOTES_MESSAGES)
                    for chat_id in chat_ids:
                        try:
                            await client.send_message(chat_id, random_quote)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"[Scheduler] فشل في إرسال الاقتباس إلى {chat_id}: {e}")
            except Exception as e:
                print(f"[Scheduler] حدث خطأ في قسم إرسال الاقتباسات: {e}")