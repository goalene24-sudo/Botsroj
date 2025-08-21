# plugins/developer.py
import random
import time
from telethon import events
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors.rpcerrorlist import UserNotParticipantError
from bot import client
import config
from .utils import db, is_admin, add_points, save_db

@client.on(events.NewMessage(pattern="^نشاطك$"))
async def activity_report_handler(event):
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return

    loading_msg = await event.reply("🔎 | **جاري جمع البيانات من المجموعات النشطة...**\nقد يستغرق هذا بعض الوقت.")
    
    report_parts = ["📊 **تقرير نشاط البوت سُـرُوچ**\n\n"]
    active_groups_count = 0

    all_chat_ids = [int(chat_id) for chat_id in db if chat_id.startswith('-')]

    for chat_id in all_chat_ids:
        chat_id_str = str(chat_id)
        chat_info = db[chat_id_str]
        
        if chat_info.get("is_paused", False) or "users" not in chat_info:
            continue

        try:
            if not await is_admin(chat_id, 'me'):
                continue

            chat_entity = await client.get_entity(chat_id)
            member_count = (await client.get_participants(chat_entity, limit=0)).total
            
            admins_text = ""
            async for user in client.iter_participants(chat_entity, filter=ChannelParticipantsAdmins):
                admins_text += f"   - [{user.first_name}](tg://user?id={user.id})\n"
            
            active_groups_count += 1
            report_parts.append(
                f"**========================**\n"
                f"**● المجموعة:** {chat_entity.title}\n"
                f"**● الآيدي:** `{chat_id}`\n"
                f"**● عدد الأعضاء:** {member_count}\n"
                f"**● قائمة المشرفين:**\n{admins_text if admins_text else '   - لا يوجد مشرفين.'}\n"
            )
        except (UserNotParticipantError, ValueError):
            continue
        except Exception:
            continue

    if active_groups_count > 0:
        final_report = "".join(report_parts)
        final_report += f"\n**========================**\n**📈 | ملخص: البوت نشط حالياً في {active_groups_count} مجموعة.**"
        
        if len(final_report) > 4096:
            with open("activity_report.txt", "w", encoding="utf-8") as f:
                f.write(final_report)
            await loading_msg.delete()
            await client.send_file(event.chat_id, "activity_report.txt", caption="**التقرير طويل جداً، تم إرساله كملف.**")
        else:
            await loading_msg.edit(final_report, link_preview=False)
    else:
        await loading_msg.edit("**ℹ️ | لا توجد أي مجموعات نشطة حالياً.**")

@client.on(events.NewMessage(pattern="^سحب اليانصيب$"))
async def lottery_draw_handler(event):
    if event.is_private or event.sender_id not in config.SUDO_USERS:
        return

    chat_id_str = str(event.chat_id)
    
    lottery_players = db.get(chat_id_str, {}).get("lottery_players", [])
    if not lottery_players:
        return await event.reply("**لا يوجد أي مشاركين في اليانصيب الحالي لبدء السحب.**")

    await event.reply(f"**🥁 | بدأ سحب اليانصيب!**\n\n**لدينا {len(lottery_players)} تذكرة مشاركة...**")
    time.sleep(2)

    try:
        winner_id_str = random.choice(lottery_players)
        winner_user = await client.get_entity(int(winner_id_str))
        
        prize = random.randint(5000, 15000)
        
        add_points(event.chat_id, int(winner_id_str), prize)
        
        announcement = (
            f"🎉 **الفائز المحظوظ هو... [{winner_user.first_name}](tg://user?id={winner_user.id})!** 🎉\n\n"
            f"**ربحت جائزة كبرى قدرها `{prize}` نقطة! 🥳**\n\n"
            f"**مبروك! تم إغلاق السحب الحالي وبدء دورة جديدة. اشتروا تذاكركم الآن!**"
        )
        await event.reply(announcement)
        
        db[chat_id_str]["lottery_players"] = []
        save_db(db)

    except Exception as e:
        await event.reply(f"**حدث خطأ أثناء إجراء السحب:**\n`{e}`")
