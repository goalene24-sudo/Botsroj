import asyncio
import random
import re
from sqlalchemy.future import select
from telethon import events
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin
from telethon.errors.rpcerrorlist import ChatWriteForbiddenError

# استيرادات محلية
# --- (تم التعديل هنا) ---
from bot import client
from config import OWNER_ID
from database import AsyncDBSession
from models import Chat

# --- قوائم الرسائل ---

DHIKR_MESSAGES = [
    "سبحان الله", "الحمد لله", "لا إله إلا الله", "الله أكبر", "سبحان الله وبحمده", "سبحان الله العظيم",
    "أستغفر الله وأتوب إليه", "لا حول ولا قوة إلا بالله", "اللهم صل على نبينا محمد",
    "حسبي الله لا إله إلا هو عليه توكلت وهو رب العرش العظيم"
]

QUOTES_MESSAGES = [
    "“كن أنت التغيير الذي تريد أن تراه في العالم.” - غاندي",
    "“العقل الذي يفتح لفكرة جديدة لن يعود أبداً إلى حجمه الأصلي.” - ألبرت أينشتاين",
    "“النجاح ليس نهائياً، والفشل ليس قاتلاً: إنما الشجاعة للاستمرار هي التي تهم.” - ونستون تشرشل",
    "“الحياة إما مغامرة جريئة أو لا شيء على الإطلاق.” - هيلين كيلر",
    "“الطريقة الوحيدة للقيام بعمل عظيم هي أن تحب ما تفعله.” - ستيف جوبز"
]

# --- دالة للتحقق من صلاحيات المشرف ---

async def is_admin_or_owner(event) -> bool:
    if event.sender_id == OWNER_ID:
        return True
    try:
        participant = await client.get_participant(event.chat_id, event.sender_id)
        if isinstance(participant, (ChannelParticipantCreator, ChannelParticipantAdmin)):
            return True
    except Exception:
        return False
    return False

# --- أوامر التحكم ---

@client.on(events.NewMessage(pattern=r"^[!/](تفعيل الاذكار|enable_dhikr)$", func=lambda e: e.is_group))
async def enable_dhikr_command(event):
    if not await is_admin_or_owner(event):
        return await event.reply("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")
    async with AsyncDBSession() as session:
        chat = await session.get(Chat, event.chat_id)
        if not chat: return
        if chat.dhikr_enabled:
            await event.reply("**ميزة الأذكار التلقائية مفعلة بالفعل.**")
        else:
            chat.dhikr_enabled = True
            await session.commit()
            await event.reply("**✅ تم تفعيل ميزة الأذكار التلقائية بنجاح.**\n**سيرسل البوت ذكرًا كل ساعة.**")

@client.on(events.NewMessage(pattern=r"^[!/](تعطيل الاذكار|disable_dhikr)$", func=lambda e: e.is_group))
async def disable_dhikr_command(event):
    if not await is_admin_or_owner(event):
        return await event.reply("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")
    async with AsyncDBSession() as session:
        chat = await session.get(Chat, event.chat_id)
        if not chat: return
        if not chat.dhikr_enabled:
            await event.reply("**ميزة الأذكار التلقائية معطلة بالفعل.**")
        else:
            chat.dhikr_enabled = False
            await session.commit()
            await event.reply("**❌ تم تعطيل ميزة الأذكار التلقائية بنجاح.**")

@client.on(events.NewMessage(pattern=r"^[!/](تفعيل الاقتباسات|enable_quotes)$", func=lambda e: e.is_group))
async def enable_quotes_command(event):
    if not await is_admin_or_owner(event):
        return await event.reply("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")
    async with AsyncDBSession() as session:
        chat = await session.get(Chat, event.chat_id)
        if not chat: return
        if chat.quotes_enabled:
            await event.reply("**ميزة الاقتباسات التلقائية مفعلة بالفعل.**")
        else:
            chat.quotes_enabled = True
            await session.commit()
            await event.reply("**✅ تم تفعيل ميزة الاقتباسات التلقائية بنجاح.**\n**سيرسل البوت اقتباسًا كل ساعة.**")

@client.on(events.NewMessage(pattern=r"^[!/](تعطيل الاقتباسات|disable_quotes)$", func=lambda e: e.is_group))
async def disable_quotes_command(event):
    if not await is_admin_or_owner(event):
        return await event.reply("**عذرًا، هذا الأمر مخصص للمشرفين ومطور البوت فقط.**")
    async with AsyncDBSession() as session:
        chat = await session.get(Chat, event.chat_id)
        if not chat: return
        if not chat.quotes_enabled:
            await event.reply("**ميزة الاقتباسات التلقائية معطلة بالفعل.**")
        else:
            chat.quotes_enabled = False
            await session.commit()
            await event.reply("**❌ تم تعطيل ميزة الاقتباسات التلقائية بنجاح.**")

# --- المهمة الدورية (Scheduler) ---

async def scheduler_task():
    print(">> مهمة الرسائل الدورية (الأذكار والاقتباسات) قد بدأت. <<")
    minute_counter = 0
    while True:
        await asyncio.sleep(60)
        minute_counter += 1
        if minute_counter % 60 == 0:
            # إرسال الأذكار
            try:
                async with AsyncDBSession() as session:
                    stmt_dhikr = select(Chat.id).where(Chat.dhikr_enabled == True)
                    result_dhikr = await session.execute(stmt_dhikr)
                    dhikr_chat_ids = result_dhikr.scalars().all()
                if dhikr_chat_ids:
                    random_dhikr = random.choice(DHIKR_MESSAGES)
                    for chat_id in dhikr_chat_ids:
                        try:
                            await client.send_message(chat_id, f"**{random_dhikr}**")
                            await asyncio.sleep(0.5)
                        except (ChatWriteForbiddenError, ValueError):
                             print(f"[Scheduler] لا يمكن الإرسال إلى {chat_id} (محظور أو لم يعد موجودًا).")
                        except Exception as e:
                            print(f"[Scheduler] فشل في إرسال الذكر إلى {chat_id}: {e}")
            except Exception as e:
                print(f"[Scheduler] حدث خطأ في قسم إرسال الأذكار: {e}")
            
            # إرسال الاقتباسات
            try:
                async with AsyncDBSession() as session:
                    stmt_quotes = select(Chat.id).where(Chat.quotes_enabled == True)
                    result_quotes = await session.execute(stmt_quotes)
                    quotes_chat_ids = result_quotes.scalars().all()
                if quotes_chat_ids:
                    random_quote = random.choice(QUOTES_MESSAGES)
                    for chat_id in quotes_chat_ids:
                        try:
                            await client.send_message(chat_id, f"**{random_quote}**")
                            await asyncio.sleep(0.5)
                        except (ChatWriteForbiddenError, ValueError):
                             print(f"[Scheduler] لا يمكن الإرسال إلى {chat_id} (محظور أو لم يعد موجودًا).")
                        except Exception as e:
                            print(f"[Scheduler] فشل في إرسال الاقتباس إلى {chat_id}: {e}")
            except Exception as e:
                print(f"[Scheduler] حدث خطأ في قسم إرسال الاقتباسات: {e}")
