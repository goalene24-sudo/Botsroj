# plugins/media_search.py
import os
import random
import asyncio
from telethon import events
from bot import client
from .utils import check_activation
from duckduckgo_search import DDGS
from youtubesearchpython import VideosSearch
import yt_dlp

@client.on(events.NewMessage(pattern=r"^صورة (.+)"))
async def image_search_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    search_term = event.pattern_match.group(1).strip()
    if not search_term:
        return await event.reply("**شنو الصورة اللي أدور عليها؟ اكتب شي ويه الأمر.**\n**مثال: `صورة قطة`**")

    loading_msg = await event.reply(f"**📷 لحظات... دا أدور على صورة لـ '{search_term}'**")

    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.images(search_term, max_results=50)]
        
        if not results:
            return await loading_msg.edit(f"**عذراً، ما لگيت أي صورة تطابق بحثك عن '{search_term}'.\nحاول بكلمات بحث مختلفة.**")
        
        image_to_send = random.choice(results)
        image_url = image_to_send['image']
        
        await client.send_file(
            event.chat_id,
            file=image_url,
            caption=f"**🖼️ | نتيجة البحث عن:** `{search_term}`",
            reply_to=event.id
        )
        await loading_msg.delete()

    except Exception as e:
        await loading_msg.edit(f"**عذراً، حدث خطأ أثناء البحث عن الصورة.\n`{e}`**")


@client.on(events.NewMessage(pattern=r"^يوت (.+)"))
async def youtube_search_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    search_term = event.pattern_match.group(1).strip()
    if not search_term:
        return await event.reply("**شنو الفيديو اللي أدور عليه؟ اكتب شي ويه الأمر.**\n**مثال: `يوت اغنية انت ايه`**")

    msg = await event.reply(f"**🔎 | جاري البحث عن `{search_term}` في يوتيوب...**")

    try:
        videos_search = VideosSearch(search_term, limit=1)
        results = videos_search.result()
        if not results['result']:
            return await msg.edit(f"**عذراً، لم أجد أي نتائج لـ `{search_term}`.**")

        video_url = results['result'][0]['link']
        video_title = results['result'][0]['title']
        
        await msg.edit(f"**✅ | تم العثور على الأغنية.**\n**🎵 | العنوان:** `{video_title}`\n\n**📥 | جاري التحميل الآن...**")

        # التأكد من وجود مجلد للتحميلات
        if not os.path.isdir('downloads'):
            os.makedirs('downloads')

        output_path = f"downloads/{video_title}.mp3"
        
        # إعدادات التحميل
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }

        # التحميل
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        await msg.edit("**📤 | جاري الرفع الآن...**")

        # إرسال الملف الصوتي
        await client.send_file(
            event.chat_id,
            file=output_path,
            caption=f"**🎵 | تم تحميل:** `{video_title}`",
            reply_to=event.id,
            attributes=[] 
        )
        
        await msg.delete()
        # حذف الملف بعد رفعه لتوفير المساحة
        if os.path.exists(output_path):
            os.remove(output_path)

    except Exception as e:
        await msg.edit(f"**❌ | حدث خطأ أثناء جلب المقطع.**\n\n**الخطأ:** `{e}`")
