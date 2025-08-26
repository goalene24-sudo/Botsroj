# plugins/diag_test.py
import traceback
from telethon import events
from bot import client

@client.on(events.NewMessage(pattern=r"^فحص$"))
async def diagnose_history(event):
    """
    أمر تشخيصي بسيط لاختبار القدرة على قراءة سجل الرسائل.
    """
    # لا نحتاج لفحص الصلاحيات هنا لأننا نريد اختبار الاتصال الأساسي
    await event.reply("🔬 **بدء اختبار التشخيص... سأحاول الآن قراءة آخر 5 رسائل من سجل هذه المجموعة.**")
    try:
        messages = []
        # أبسط طلب ممكن لقراءة السجل
        async for msg in client.iter_messages(event.chat_id, limit=5):
            messages.append(msg.id)
        
        # إذا اكتملت الحلقة بدون خطأ، فهذا يعني أن العملية نجحت
        await event.reply(f"✅ **نجح الاختبار!**\n\nتمكنت من قراءة وتحديد {len(messages)} رسالة من السجل بنجاح. هذا يعني أن المشكلة الغامضة تكمن في مكان آخر غير الاتصال الأساسي.")

    except Exception as e:
        # إذا فشل، سيظهر نفس الخطأ الذي نواجهه
        traceback.print_exc()
        error_name = type(e).__name__
        error_description = str(e)
        await event.reply(
            f"**❗ فشل الاختبار بنفس الخطأ السابق ❗**\n\n"
            f"**نوع الخطأ:**\n`{error_name}`\n\n"
            f"**الوصف التقني:**\n`{error_description}`\n\n"
            "**الاستنتاج النهائي: المشكلة ليست في كود البوت، بل في الاتصال بين حسابك/بوتك وتليجرام فيما يخص قراءة السجل.**"
        )