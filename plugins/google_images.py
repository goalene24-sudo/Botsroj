import os
import shutil
from telethon import events
from telethon.tl.types import InputMediaPhoto

# استيراد مكتبة البحث التي أنشأناها في الملف الأول
from helpers.gimage_scraper import googleimagesdownload

# استيراد متغير البوت بالطريقة الصحيحة
from bot import client

# استيراد الوحدات المساعدة من بوتك
from .utils import check_activation

# تعريف الأمر الجديد
@client.on(events.NewMessage(pattern=r"^\.صور(?: (\d+))? (.*)$"))
async def google_image_search(event):
    """
    .صور [العدد] <نص البحث>
    يبحث عن الصور في جوجل ويرسلها. العدد اختياري، الافتراضي هو 1.
    """
    # التحقق مما إذا كان البوت مفعل في المجموعة
    if not await check_activation(event.chat_id):
        return

    # رسالة أولية لإعلام المستخدم بالبدء
    reply_msg = await event.reply("**... جاري البحث عن الصور، يرجى الانتظار**")

    # تحديد مجلد مؤقت لتنزيل الصور
    temp_download_dir = "./temp_gimages/"
    if not os.path.isdir(temp_download_dir):
        os.makedirs(temp_download_dir)

    # استخلاص العدد ونص البحث من رسالة المستخدم
    match = event.pattern_match.groups()
    limit = int(match[0]) if match[0] else 1
    query = match[1]

    # التأكد من أن العدد لا يتجاوز حدًا معينًا (مثلاً 10) لحماية البوت
    if limit > 10:
        await reply_msg.edit("**الحد الأقصى للصور في كل مرة هو 10 صور.**")
        return

    # إعداد الوسائط (arguments) لمكتبة البحث
    arguments = {
        "keywords": query,
        "limit": limit,
        "output_directory": temp_download_dir,
        "no_directory": True, # لمنع إنشاء مجلدات فرعية
        "safe_search": True,
    }

    try:
        # إنشاء كائن من مكتبة البحث
        scraper = googleimagesdownload()
        # بدء عملية البحث والتنزيل
        paths, errors = scraper.download(arguments)
        
        # قائمة لتخزين مسارات الصور التي تم تنزيلها
        downloaded_paths = []
        if paths:
            # paths يكون قاموسًا، نحتاج إلى استخلاص المسارات الفعلية
            for key in paths:
                downloaded_paths.extend(paths[key])
        
        if not downloaded_paths:
            await reply_msg.edit(f"**لم يتم العثور على أي صور لكلمة البحث:** `{query}`")
            return

        # إرسال الصور التي تم تنزيلها
        reply_to_id = event.message.reply_to_msg_id or event.id
        if limit == 1:
            await client.send_file(event.chat_id, downloaded_paths[0], reply_to=reply_to_id)
        else:
            # استخدام ألبوم إذا كان العدد أكثر من صورة
            media_album = [InputMediaPhoto(path) for path in downloaded_paths]
            await client.send_file(event.chat_id, media_album, reply_to=reply_to_id)
        
        # حذف الرسالة الأولية
        await reply_msg.delete()

    except Exception as e:
        # إبلاغ المستخدم في حال حدوث خطأ
        await reply_msg.edit(f"**حدث خطأ أثناء البحث:**\n`{str(e)}`")
    
    finally:
        # خطوة مهمة: حذف المجلد المؤقت وكل محتوياته لتنظيف السيرفر
        if os.path.isdir(temp_download_dir):
            shutil.rmtree(temp_download_dir)
