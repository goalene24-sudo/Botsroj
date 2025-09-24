import os
import random
import asyncio
import aiohttp
from telethon import events
from telethon.tl.types import InputMediaPhoto
from bot import client
import config  # --- (مهم) استيراد ملف الإعدادات ---
from .utils import check_activation
import yt_dlp
import logging # <-- تمت الإضافة هنا

logger = logging.getLogger(__name__) # <-- تمت الإضافة هنا

# --- (مُعدل بالكامل) دالة البحث عن الصور باستخدام Google API ---
@client.on(events.NewMessage(pattern=r"^صورة(?: (\d+))? (.+)"))
async def image_search_handler(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    # التحقق من وجود المفاتيح في ملف الإعدادات
    if not hasattr(config, 'GOOGLE_API_KEY') or not hasattr(config, 'GOOGLE_CX_ID') or not config.GOOGLE_API_KEY or not config.GOOGLE_CX_ID:
        await event.reply("**❌ | خطأ فادح!**\n\nلم يتم العثور على مفاتيح Google API في ملف الإعدادات. يرجى إضافتها أولاً.")
        return

    match = event.pattern_match.groups()
    limit = int(match[0]) if match[0] else 1
    search_term = match[1].strip()

    if not search_term:
        return await event.reply("**شنو الصورة اللي أدور عليها؟ اكتب شي ويه الأمر.**\n**مثال: `صورة قطة`**")
    
    if limit > 10:
        limit = 10 # الحد الأقصى للـ API هو 10 في كل طلب

    loading_msg = await event.reply(f"**📷 لحظات... دا أدور على صورة لـ '{search_term}' باستخدام Google**")

    api_key = config.GOOGLE_API_KEY
    cx_id = config.GOOGLE_CX_ID
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx_id,
        "q": search_term,
        "searchType": "image",
        "num": limit,
        "safe": "active"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return await loading_msg.edit(f"**❌ | حدث خطأ من Google:**\n`{response.status}: {error_text}`")
                
                data = await response.json()

        if "items" not in data or not data["items"]:
            return await loading_msg.edit(f"**عذراً، ما لگيت أي صورة تطابق بحثك عن '{search_term}'.\nحاول بكلمات بحث مختلفة.**")

        results = [item['link'] for item in data['items']]
        
        reply_to_id = event.message.reply_to_msg_id or event.id
        if limit == 1:
            await client.send_file(event.chat_id, results[0], caption=f"**🖼️ | نتيجة البحث عن:** `{search_term}`", reply_to=reply_to_id)
        else:
            media_album = [InputMediaPhoto(url) for url in results]
            await client.send_file(event.chat_id, media_album, reply_to=reply_to_id)
        
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
        # =========================================================
        # | START OF MODIFIED CODE | بداية الكود المعدل            |
        # =========================================================
        ydl_opts_search = {
            'quiet': True,       # <-- لجعل yt-dlp هادئة
            'noprogress': True,  # <-- لإخفاء شريط التقدم
            'logger': logger,    # <-- لتوجيه رسائل yt-dlp إلى سجلنا الخاص
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
            'quiet': True,       # <-- لجعل yt-dlp هادئة
            'noprogress': True,  # <-- لإخفاء شريط التقدم
            'logger': logger,    # <-- لتوجيه رسائل yt-dlp إلى سجلنا الخاص
            'noplaylist': True,
            'cookiefile': cookies_file
        }

        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([video_url])
        # =========================================================
        # | END OF MODIFIED CODE | نهاية الكود المعدل              |
        # =========================================================
        
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
