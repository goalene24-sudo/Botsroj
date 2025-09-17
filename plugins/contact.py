import json
from telethon import events
from sqlalchemy.future import select

from bot import client
import config
# --- (تم التعديل) استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import GlobalSetting

# --- (جديد) دوال مساعدة للتعامل مع جلسات التواصل في قاعدة البيانات ---
async def get_contact_sessions(session):
    """تجلب وتفك ترميز قاموس جلسات التواصل."""
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == "contact_sessions"))
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except json.JSONDecodeError:
            return {}
    return {}

async def save_contact_sessions(session, sessions_dict):
    """ترميز وحفظ قاموس جلسات التواصل."""
    json_value = json.dumps(sessions_dict)
    result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == "contact_sessions"))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = json_value
    else:
        setting = GlobalSetting(key="contact_sessions", value=json_value)
        session.add(setting)
    # سيتم تنفيذ commit في الدالة الرئيسية بعد استدعاء هذه الدالة

# هذا الجزء يستقبل الرسائل من المستخدمين ويوجهها إليك
@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id not in config.SUDO_USERS))
async def forward_to_owner(event):
    try:
        # إعادة توجيه الرسالة إلى أول مطور في القائمة (أنت)
        forwarded_message = await client.forward_messages(config.SUDO_USERS[0], event.message)
        
        async with AsyncDBSession() as session:
            sessions = await get_contact_sessions(session)
            
            # حفظ معرف رسالتك الجديدة مع معرف المستخدم الأصلي
            sessions[str(forwarded_message.id)] = event.sender_id
            
            await save_contact_sessions(session, sessions)
            await session.commit()

        # إرسال رسالة تأكيد للمستخدم
        await event.reply("✅ تم إرسال رسالتك إلى المطور، شكراً لتواصلك.")
    except Exception as e:
        print(f"[CONTACT PLUGIN] Failed to forward message from {event.sender_id}. Error: {e}")


# هذا الجزء الجديد يستقبل ردودك ويوجهها للمستخدمين
@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id in config.SUDO_USERS and e.is_reply))
async def reply_to_user(event):
    # الحصول على معرف الرسالة التي ترد عليها
    replied_to_id = str(event.reply_to_msg_id)
    
    async with AsyncDBSession() as session:
        contact_sessions = await get_contact_sessions(session)
        
        if replied_to_id in contact_sessions:
            user_id = contact_sessions[replied_to_id]
            
            try:
                # إرسال رسالتك (الرد) إلى المستخدم الأصلي
                await client.send_message(user_id, event.message)
                
            except Exception as e:
                await event.reply(f"⚠️ لم أتمكن من إرسال الرد إلى المستخدم. قد يكون قد قام بحظر البوت.\n\n**الخطأ:** `{e}`")
