# plugins/logo.py
import os
from PIL import Image, ImageDraw, ImageFont
import httpx
from telethon import events
from bot import client
from .utils import check_activation

# --- إعدادات اللوجو ---
if not os.path.isdir("./temp"):
    os.makedirs("./temp")

LOGO_STYLES = {
    "نار": {
        "bg_url": "https://i.imgur.com/2Qk4a2d.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/space-age.ttf",
        "color": "#FFC300",
        "stroke_color": "#C70039",
        "stroke_width": 4,
        "size": 180
    },
    "فخم": {
        "bg_url": "https://i.imgur.com/s4p4a6M.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/TheGreatVibes.ttf",
        "color": "#E7C581",
        "stroke_color": "#1C1C1C",
        "stroke_width": 2,
        "size": 220
    },
    "كرتون": {
        "bg_url": "https://i.imgur.com/f04uC17.jpeg",
        "font_url": "https://github.com/Jisan09/Files/raw/main/fonts/Grobold.ttf",
        "color": "#FFFFFF",
        "stroke_color": "#000000",
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

# --- (تم التعديل) الدالة الآن تعيد رسالة الخطأ لتشخيص المشكلة ---
async def download_file(url, output_path):
    if not os.path.exists(output_path):
        try:
            async with httpx.AsyncClient() as http_client:
                # إضافة رأس متصفح لتجنب الحجب
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
                response = await http_client.get(url, headers=headers, follow_redirects=True, timeout=20)
                response.raise_for_status()
                with open(output_path, 'wb') as f:
                    f.write(response.content)
            return True, None
        except Exception as e:
            # طباعة الخطأ في السجل وإعادته كنص
            error_message = f"فشل تحميل {url}: {e}"
            print(error_message)
            return False, str(e)
    return True, None


@client.on(events.NewMessage(pattern=r"^لوجو(?:\s+([\S]+))?\s+([\s\S]+)"))
async def logo_creator(event):
    if event.is_private or not await check_activation(event.chat_id):
        return

    zed = await event.reply("`جارِ صناعة اللوجو...`")

    style_name = event.pattern_match.group(1)
    text = event.pattern_match.group(2)

    if style_name and style_name in LOGO_STYLES:
        style = LOGO_STYLES[style_name]
    else:
        text = f"{style_name} {text}" if style_name else text
        style = LOGO_STYLES["default"]
        style_name = "default"

    bg_path = f"./temp/{style_name}_bg.jpg"
    font_path = f"./temp/{style_name}_font.ttf"

    # --- (تم التعديل) التقاط رسالة الخطأ من الدالة ---
    bg_success, bg_error = await download_file(style["bg_url"], bg_path)
    if not bg_success:
        await zed.edit(f"**- عذراً .. فشل تحميل الخلفية 🖼️**\n\n**- السبب:**\n`{bg_error}`")
        return

    font_success, font_error = await download_file(style["font_url"], font_path)
    if not font_success:
        await zed.edit(f"**- عذراً .. فشل تحميل الخط ✍️**\n\n**- السبب:**\n`{font_error}`")
        return

    try:
        img = Image.open(bg_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, style["size"])

        img_width, img_height = img.size
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (img_width - text_width) / 2
        y = (img_height - text_height) / 2 - (img_height * 0.05)

        draw.text(
            (x, y),
            text,
            font=font,
            fill=style["color"],
            stroke_width=style["stroke_width"],
            stroke_fill=style["stroke_color"],
            align="center"
        )
        
        output_path = f"./temp/{event.id}_logo.png"
        img.save(output_path, "PNG")

        await event.client.send_file(
            event.chat_id,
            output_path,
            reply_to=event.message.reply_to_msg_id or event.id
        )
        
        if os.path.exists(output_path):
            os.remove(output_path)
        await zed.delete()

    except Exception as e:
        await zed.edit(f"**عذراً، حدث خطأ فني أثناء صناعة الصورة:**\n`{e}`")


@client.on(events.NewMessage(pattern="^ستايلات اللوجو$"))
async def list_logo_styles(event):
    if event.is_private or not await check_activation(event.chat_id):
        return
    
    styles_list = "**🎨 الستايلات المتاحة لصناعة اللوجو:**\n\n"
    for name in LOGO_STYLES:
        if name != "default":
            styles_list += f"• `{name}`\n"
    
    styles_list += "\n**للاستخدام، اكتب:** `لوجو <اسم الستايل> <النص>`\n**مثال:** `لوجو نار بوت سروج`"
    await event.reply(styles_list)
