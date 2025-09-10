# plugins/akinator_game.py
import asyncio
import akinator
from akinator import Language
import logging  # <-- تم استدعاء مكتبة التسجيل
from telethon import events, Button
from bot import client
from .utils import check_activation

# --- هذا كود مؤقت للتشخيص فقط ---

@client.on(events.NewMessage(pattern="^اكيناتور$"))
async def start_akinator(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    # سنقوم بطباعة محتويات كلاس اللغة باستخدام المسجل logging
    try:
        await event.reply("`تم إرسال البيانات إلى السجلات... يرجى مراجعة سجلات Railway الآن.`")
        logging.warning("========== قائمة اللغات المتاحة في أكيناتور ==========")
        logging.warning(dir(Language)) # سيقوم هذا الأمر بطباعة المحتويات في السجل
        logging.warning("======================================================")
    except Exception as e:
        await event.reply(f"**حدث خطأ أثناء الفحص:**\n`{e}`")

# تم تعطيل بقية الدوال مؤقتاً
