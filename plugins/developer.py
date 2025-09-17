import random
import time
from telethon import events
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors.rpcerrorlist import UserNotParticipantError, ChatWriteForbiddenError
from bot import client
import config

# --- استيراد مكونات قاعدة البيانات الجديدة ---
from sqlalchemy.future import select
# (تم التعديل) استيراد الجلسة الغير متزامنة الجديدة
from database import AsyncDBSession
from models import Chat

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import is_admin, add_points


# --- دوال مساعدة جديدة لإدارة إعدادات المجموعة ---
async def get_chat_setting(chat_id, key, default=None):
    """تجلب إعدادًا معينًا من حقل الإعدادات للمجموعة."""
    async with AsyncDBSession() as session:
        result = await session.execute(select(Chat.settings).where(Chat.id == chat_id))
        settings = result.scalar_one_or_none()
        if settings:
            return settings.get(key, default)
        return default

async def set_chat_setting(chat_id, key, value):
    """تُعيّن إعدادًا معينًا في حقل الإعدادات للمجموعة."""
    async with AsyncDBSession() as session:
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        
        if chat:
            # نستخدم نسخة قابلة للتعديل من الإعدادات
            new_settings = dict(chat.settings)
            new_settings[key] = value
            chat.settings = new_settings
            await session.commit()
        else:
            # إذا لم تكن المجموعة موجودة، ننشئها
            new_chat = Chat(id=chat_id, settings={key: value})
            session.add(new_chat)
            await session.commit()


@client.on(events.NewMessage(pattern="^نشاطك$"))
async def activity_report_handler(event):
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return

    loading_msg = await event.reply("🔎 | **جاري جمع البيانات من المجموعات النشطة...**\nقد يستغرق هذا بعض الوقت.")
    
    report_parts = ["📊 **تقرير نشاط البوت سُـرُوچ**\n\n"]
    active_groups_count = 0

    async with AsyncDBSession() as session:
        # جلب جميع المجموعات النشطة من قاعدة البيانات
        result = await session.execute(select(Chat).where(Chat.is_active == True))
        active_chats = result.scalars().all()

    for chat in active_chats:
        chat_id = chat.id
        try:
            if not await is_admin(chat_id, 'me'):
                continue

            chat_entity = await client.get_entity(chat_id)
            member_count = (await client.get_participants(chat_entity, limit=0)).total
            
            admins_text = ""
            async for user in client.iter_participants(chat_entity, filter=ChannelParticipantsAdmins):
                admins_text += f"    - [{user.first_name}](tg://user?id={user.id})\n"
            
            active_groups_count += 1
            report_parts.append(
                f"**========================**\n"
                f"**● المجموعة:** {chat_entity.title}\n"
                f"**● الآيدي:** `{chat_id}`\n"
                f"**● عدد الأعضاء:** {member_count}\n"
                f"**● قائمة المشرفين:**\n{admins_text if admins_text else '    - لا يوجد مشرفين.'}\n"
            )
        except (UserNotParticipantError, ValueError):
            continue
        except Exception as e:
            print(f"خطأ في معالجة المجموعة {chat_id} في تقرير النشاط: {e}")
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

    chat_id = event.chat_id
    
    lottery_players = await get_chat_setting(chat_id, "lottery_players", [])
    if not lottery_players:
        return await event.reply("**لا يوجد أي مشاركين في اليانصيب الحالي لبدء السحب.**")

    await event.reply(f"**🥁 | بدأ سحب اليانصيب!**\n\n**لدينا {len(lottery_players)} تذكرة مشاركة...**")
    time.sleep(2)

    try:
        winner_id_str = random.choice(lottery_players)
        winner_id = int(winner_id_str)
        winner_user = await client.get_entity(winner_id)
        
        prize = random.randint(5000, 15000)
        
        await add_points(chat_id, winner_id, prize)
        
        announcement = (
            f"🎉 **الفائز المحظوظ هو... [{winner_user.first_name}](tg://user?id={winner_user.id})!** 🎉\n\n"
            f"**ربحت جائزة كبرى قدرها `{prize}` نقطة! 🥳**\n\n"
            f"**مبروك! تم إغلاق السحب الحالي وبدء دورة جديدة. اشتروا تذاكركم الآن!**"
        )
        await event.reply(announcement)
        
        await set_chat_setting(chat_id, "lottery_players", [])

    except Exception as e:
        await event.reply(f"**حدث خطأ أثناء إجراء السحب:**\n`{e}`")

@client.on(events.NewMessage(pattern=r"^ارسل (-?\d+) (.+)"))
async def send_to_group_handler(event):
    if not event.is_private or event.sender_id not in config.SUDO_USERS:
        return

    try:
        chat_id_to_send = int(event.pattern_match.group(1))
        message_to_send = event.pattern_match.group(2)

        await client.send_message(chat_id_to_send, message_to_send)
        
        await event.reply(f"✅ **تم إرسال رسالتك بنجاح إلى المجموعة:** `{chat_id_to_send}`")

    except (ValueError, TypeError):
        await event.reply("❌ **خطأ في الصيغة.**\n\n**الاستخدام الصحيح:**\n`ارسل [معرف المجموعة] [الرسالة]`\n\n**مثال:**\n`ارسل -100123456789 مرحبا`")
    except ChatWriteForbiddenError:
        await event.reply(f"❌ **فشل الإرسال.**\n\nلا أملك صلاحية الكتابة في المجموعة `{chat_id_to_send}`. تأكد من أنني مشرف هناك.")
    except Exception as e:
        await event.reply(f"❌ **حدث خطأ غير متوقع:**\n\n`{e}`")
