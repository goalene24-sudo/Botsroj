# plugins/media_search.py
import os
import random
import asyncio
from telethon import events
from bot import client
from .utils import check_activation
from duckduckgo_search import DDGS
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
        # البحث باستخدام yt-dlp
        ydl_opts_search = {'quiet': True, 'default_search': 'ytsearch1', 'extract_flat': 'in_playlist'}
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            info = ydl.extract_info(search_term, download=False)
            
            video = None
            if info and 'entries' in info:
                # البحث عن أول نتيجة صالحة (تحتوي على رابط)
                for entry in info['entries']:
                    if entry and 'webpage_url' in entry:
                        video = entry
                        break
            
            if not video:
                return await msg.edit(f"**عذراً، لم أجد أي نتائج لـ `{search_term}`.**")

            video_url = video.get('webpage_url')
            video_title = video.get('title')

        await msg.edit(f"**✅ | تم العثور على المقطع.**\n**🎵 | العنوان:** `{video_title}`\n\n**📥 | جاري التحميل الآن (قد يستغرق بعض الوقت)...**")

        # التأكد من وجود مجلد للتحميلات
        if not os.path.isdir('downloads'):
            os.makedirs('downloads')

        output_path = f"downloads/{random.randint(1, 10000)}.mp3"
        
        # إعدادات التحميل كملف صوتي
        ydl_opts_download = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([video_url])
        
        await msg.edit("**📤 | جاري الرفع الآن...**")

        await client.send_file(
            event.chat_id,
            file=output_path,
            caption=f"**🎵 | تم تحميل:** `{video_title}`",
            reply_to=event.id
        )
        
        await msg.delete()
        if os.path.exists(output_path):
            os.remove(output_path)

    except Exception as e:
        await msg.edit(f"**❌ | حدث خطأ أثناء جلب المقطع.**\n\n**الخطأ:** `{e}`")
