# plugins/ai.py
from telethon import events
from bot import client
from .utils import check_activation, GEMINI_ENABLED

# استيراد المكتبات فقط في حال تفعيل الميزة
if GEMINI_ENABLED:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted

@client.on(events.NewMessage(pattern=r"^(اسأل|gemini)\s+(.+)"))
async def ask_gemini_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    if not GEMINI_ENABLED: 
        return await event.reply("المطور مالتي نسه يخلي مفتاح الذكاء الاصطناعي، گولوله يفعله. 😅")
    
    prompt = event.pattern_match.group(2)
    thinking_msg = await event.reply("لحظة، دا أفكر... 🤔")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = await model.generate_content_async(prompt)
        
        # التأكد من وجود نص في الرد قبل إرساله
        if response.text:
            await thinking_msg.edit(f"💡 **جوابي هو:**\n\n{response.text}")
        else:
            await thinking_msg.edit("ما عندي جواب لهذا السؤال، الظاهر انصدمت من صعوبته. 🤯")

    # --- هذا هو الجزء الذي تم تعديله ---
    # معالج خاص لخطأ نفاد الحصة (الضغط على البوت)
    except ResourceExhausted:
        await thinking_msg.edit("معرف شصار بس الظاهر تعبت من كثرة التفكير 😵‍💫... حاول تسألني مرة لخ بعد دقيقة.")

    # معالج للأخطاء العامة الأخرى
    except Exception as e:
        await thinking_msg.edit(f"ماعرف شصار بس صارت مشكلة.\n\n`{e}`")
