# plugins/logo.py
import os
from PIL import Image, ImageDraw, ImageFont
import requests
from telethon import events
from bot import client
from .utils import check_activation

# --- إعدادات اللوجو ---
# إنشاء مجلد مؤقت لحفظ الخطوط والخلفيات
if not os.path.isdir("./temp"):
    os.makedirs("./temp")

# --- تعريف الأنماط (الستايلات) ---
LOGO_STYLES = {
    "نار": {
        "bg_url": "https://i.imgur.com/2Qk4a2d.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/space-age.ttf",
        "color": "#FFC300", # لون أصفر ناري
        "stroke_color": "#C70039", # لون أحمر داكن للإطار
        "stroke_width": 4,
        "size": 180
    },
    "فخم": {
        "bg_url": "https://i.imgur.com/s4p4a6M.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/TheGreatVibes.ttf",
        "color": "#E7C581", # لون ذهبي
        "stroke_color": "#1C1C1C", # لون أسود خفيف للإطار
        "stroke_width": 2,
        "size": 220
    },
    "كرتون": {
        "bg_url": "https://i.imgur.com/f04uC17.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/Grobold.ttf",
        "color": "#FFFFFF", # أبيض
        "stroke_color": "#000000", # أسود
        "stroke_width": 5,
        "size": 200
    },
    "default": {
        "bg_url": "https://i.imgur.com/955gqE8.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/Streamster.ttf",
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 3,
        "size": 220
    }
}

def download_file(url, output_path):
    """دالة لتحميل الملفات (خلفيات أو خطوط)"""
    if not os.path.exists(output_path):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    return True


@client.on(events.NewMessage(pattern=r"^لوجو(?:\s+([\S]+))?\s+([\s\S]+)"))
async def logo_creator(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    zed = await event.reply("`جارِ صناعة اللوجو...`")

    style_name = event.pattern_match.group(1)
    text = event.pattern_match.group(2)

    # تحديد الستايل المطلوب أو استخدام الستايل الافتراضي
    if style_name and style_name in LOGO_STYLES:
        style = LOGO_STYLES[style_name]
    else:
        # إذا لم يتم تحديد ستايل، نعتبر الكلمة الأولى جزء من النص
        text = f"{style_name} {text}" if style_name else text
        style = LOGO_STYLES["default"]

    # مسارات حفظ الملفات
    bg_path = f"./temp/{style_name or 'default'}_bg.jpg"
    font_path = f"./temp/{style_name or 'default'}_font.ttf"

    # تحميل الخلفية والخط
    if not download_file(style["bg_url"], bg_path) or not download_file(style["font_url"], font_path):
        await zed.edit("**حدث خطأ أثناء تحميل موارد اللوجو. حاول مجدداً.**")
        return

    try:
        # فتح الصورة والخط
        img = Image.open(bg_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, style["size"])

        # حساب حجم النص وموقعه للتوسيط
        img_width, img_height = img.size
        text_width, text_height = draw.textsize(text, font=font)
        x = (img_width - text_width) / 2
        y = (img_height - text_height) / 2 - 30 # رفع النص للأعلى قليلاً

        # رسم النص على الصورة
        draw.text(
            (x, y),
            text,
            font=font,
            fill=style["color"],
            stroke_width=style["stroke_width"],
            stroke_fill=style["stroke_color"],
            align="center"
        )
        
        # حفظ الصورة النهائية
        output_path = f"./temp/{event.id}_logo.png"
        img.save(output_path, "PNG")

        # إرسال الصورة
        await event.client.send_file(
            event.chat_id,
            output_path,
            reply_to=event.message.reply_to_msg_id or event.id
        )
        
        # حذف الملفات المؤقتة
        if os.path.exists(output_path):
            os.remove(output_path)
        await zed.delete()

    except Exception as e:
        await zed.edit(f"**عذراً، حدث خطأ فني:**\n`{e}`")


# --- أمر لعرض الستايلات المتاحة ---
@client.on(events.NewMessage(pattern="^ستايلات اللوجو$"))
async def list_logo_styles(event):
    if event.is_private or not await check_activation(event.chat_id):
        return
    
    styles_list = "**🎨 الستايلات المتاحة لصناعة اللوجو:**\n\n"
    for name in LOGO_STYLES:
        if name != "default":
            styles_list += f"• `{name}`\n"
    
    styles_list += "\n**للاستخدام، اكتب:** `لوجو <اسم الستايل> <النص>`"
    await event.reply(styles_list)