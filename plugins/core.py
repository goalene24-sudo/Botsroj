import logging
from telethon import events
from bot import client

# هذا السطر للتأكد من أن اللوجر يعمل
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

logger.info(">>> ملف core.py للاختبار يعمل الآن! <<<")
print(">>> ملف core.py للاختبار يعمل الآن! <<<")

@client.on(events.NewMessage(pattern="/ping"))
async def ping_handler(event):
    logger.info(">>> تم استلام أمر /ping بنجاح! <<<")
    print(">>> تم استلام أمر /ping بنجاح! <<<")
    await event.reply("Pong!")
