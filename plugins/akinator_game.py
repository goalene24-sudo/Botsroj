# plugins/akinator_game.py
import asyncio
import akinator
from akinator import Language
from telethon import events, Button
from bot import client
from .utils import check_activation

# --- هذا كود مؤقت للتشخيص فقط ---

@client.on(events.NewMessage(pattern="^اكيناتور$"))
async def start_akinator(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    # سنقوم بطباعة محتويات كلاس اللغة لمعرفة الأسماء الصحيحة
    try:
        await event.reply("`جاري فحص المكتبة... يرجى مراجعة سجلات Railway الآن.`")
        print("========== قائمة اللغات المتاحة في أكيناتور ==========")
        print(dir(Language))
        print("======================================================")
    except Exception as e:
        await event.reply(f"**حدث خطأ أثناء الفحص:**\n`{e}`")

# تم تعطيل بقية الدوال مؤقتاً
# ACTIVE_AKI_GAMES = {}
# def build_aki_buttons(chat_id, user_id): ...
# async def handle_akinator_answer(event): ...
