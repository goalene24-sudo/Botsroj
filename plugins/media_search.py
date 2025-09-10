# plugins/media_search.py
import os
import random
import asyncio
import json
import urllib.request
from urllib.parse import quote_plus
from telethon import events
from bot import client
from .utils import check_activation
import yt_dlp

# --- (جديد) قائمة هويات المتصفحات لتجنب الحظر ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

# --- (مُعدل بالكامل) دالة البحث عن الصور الجديدة ---
async def search_images(query):
    """
    يبحث عن الصور باستخدام DuckDuckGo بطريقة تحاكي المتصفح لتجنب الحظر.
    """
    url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={quote_plus(query)}&vqd_required=1"
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    request = urllib.request.Request(url, headers=headers)
    
    # محاولة لـ3 مرات في حال فشل الاتصال
    for _ in range(3):
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read())
                return [img['image'] for img in data.get('results', [])]
        except Exception:
            await asyncio.sleep(0.5) # انتظار بسيط قبل المحاولة التالية
    return []


@client.on(events.NewMessage(pattern=r"^صورة (.+)"))
async def image_search_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    search_term = event.pattern_match.group(1).strip()
    if not search_term:
        return await event.reply("**شنو الصورة اللي أدور عليها؟ اكتب شي ويه الأمر.**\n**مثال: `صورة قطة`**")

    loading_msg = await event.reply(f"**📷 لحظات... دا أدور على صورة لـ '{search_term}'**")

    try:
        # استخدام دالة البحث الجديدة والمحسّنة
        results = await search_images(search_term)
        
        if not results:
            return await loading_msg.edit(f"**عذراً، ما لگيت أي صورة تطابق بحثك عن '{search_term}'.\nحاول بكلمات بحث مختلفة.**")
        
        image_url = random.choice(results)
        
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
    
    output_path = "downloads/audio.mp3"
    cookies_file = "cookies.txt"

    if not os.path.exists(cookies_file):
        return await msg.edit("**❌ | خطأ إعداد!**\n\n**ملف `cookies.txt` غير موجود. يرجى رفعه إلى ملفات البوت لحل مشكلة التحميل من يوتيوب.**")

    try:
        ydl_opts_search = {
            'quiet': True,
            'default_search': 'ytsearch1',
            'extract_flat': 'in_playlist',
            'cookiefile': cookies_file
        }
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search_term}", download=False)
            
            video = None
            if info and 'entries' in info and info['entries']:
                video = info['entries'][0]
            
            if not video:
                return await msg.edit(f"**عذراً، لم أجد أي نتائج لـ `{search_term}`.**")

            video_url = video.get('webpage_url') or f"https://www.youtube.com/watch?v={video.get('id')}"
            video_title = video.get('title')

        await msg.edit(f"**✅ | تم العثور على المقطع.**\n**🎵 | العنوان:** `{video_title}`\n\n**📥 | جاري التحميل الآن (قد يستغرق بعض الوقت)...**")

        if not os.path.isdir('downloads'):
            os.makedirs('downloads')
        
        ydl_opts_download = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/audio',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
            'noplaylist': True,
            'cookiefile': cookies_file
        }

        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([video_url])
        
        if not os.path.exists(output_path):
            return await msg.edit("**❌ | فشلت عملية معالجة الملف بعد تحميله.**")

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
