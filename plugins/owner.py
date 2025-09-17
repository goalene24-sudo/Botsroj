# plugins/owner.py
import sys
import os
import asyncio
from telethon import events
from bot import client
import config

@client.on(events.NewMessage(pattern=r"^/اعاده التشغيل$"))
async def restart_handler(event):
    # التأكد من أن الأمر جاء منك وفي الخاص فقط
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return
        
    await event.reply("**✅ حسناً، جاري إعادة تشغيل البوت الآن...**")
    
    # تنفيذ أمر إعادة التشغيل
    os.execl(sys.executable, sys.executable, *sys.argv)


@client.on(events.NewMessage(pattern=r"^/ايقاف$"))
async def shutdown_handler(event):
    # التأكد من أن الأمر جاء منك وفي الخاص فقط
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return

    await event.reply("**✅ تم إيقاف البوت بنجاح. لن أستجيب للأوامر حتى يتم تشغيلي يدوياً مرة أخرى من الاستضافة.**")
    
    # تنفيذ أمر الإيقاف الكامل
    sys.exit()