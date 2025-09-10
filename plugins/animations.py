# plugins/animations.py
import asyncio
from collections import deque
from telethon import events
from . import zedub
from ..core.managers import edit_or_reply
from ..helpers.utils import _format
from . import ALIVE_NAME

DEFAULTUSER = str(ALIVE_NAME) if ALIVE_NAME else "Zed"

@zedub.zed_cmd(pattern="غبي$")
async def ghabe(event):
    if event.fwd_from:
        return
    animation_interval = 0.3
    animation_ttl = range(14)
    zdd = await edit_or_reply(event, "🧠.")
    animation_chars = [
        "**- عقلك** ⬅️ 🧠\n\n🧠           <(^.^ <) 🗑",
        "**- عقلك** ⬅️ 🧠\n\n🧠         <(^.^ <)   🗑",
        "**- عقلك** ⬅️ 🧠\n\n🧠       <(^.^ <)     🗑",
        "**- عقلك** ⬅️ 🧠\n\n🧠     <(^.^ <)       🗑",
        "**- عقلك** ⬅️ 🧠\n\n🧠   <(^.^ <)         🗑",
        "**- عقلك** ⬅️ 🧠\n\n🧠 <(^.^ <)           🗑",
        "**- عقلك** ⬅️ 🧠\n\n(> ^.^)>🧠            🗑",
        "**- عقلك** ⬅️ 🧠\n\n  (> ^.^)>🧠          🗑",
        "**- عقلك** ⬅️ 🧠\n\n    (> ^.^)>🧠        🗑",
        "**- عقلك** ⬅️ 🧠\n\n      (> ^.^)>🧠      🗑",
        "**- عقلك** ⬅️ 🧠\n\n         (> ^.^)>🧠   🗑",
        "**- عقلك** ⬅️ 🧠\n\n           (> ^.^)>🧠 🗑",
        "**- عقلك** ⬅️ 🧠\n\n🗑️             (> ^.^)>",
        "**- عقلك** ⬅️ 🗑️",
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zdd.edit(animation_chars[i % 14])

@zedub.zed_cmd(pattern="قنابل$")
async def bomd(event):
    if event.fwd_from:
        return
    animation_interval = 0.4
    animation_ttl = range(13)
    zdd = await edit_or_reply(event, "💣")
    animation_chars = [
        "💣\n\n\n\n\n",
        "💣\n💣\n\n\n\n",
        "💣\n💣\n💣\n\n\n",
        "💣\n💣\n💣\n💣\n\n",
        "💣\n💣\n💣\n💣\n💣",
        "💥\n💣\n💣\n💣\n💣",
        "💥\n💥\n💣\n💣\n💣",
        "💥\n💥\n💥\n💣\n💣",
        "💥\n💥\n💥\n💥\n💣",
        "💥\n💥\n💥\n💥\n💥",
        "🔥\n🔥\n🔥\n🔥\n🔥",
        "🔥🔥\n🔥🔥\n🔥🔥\n🔥🔥\n🔥🔥",
        "🔥🔥🔥\n🔥🔥🔥\n🔥🔥🔥\n🔥🔥🔥\n🔥🔥🔥",
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zdd.edit(animation_chars[i % 13])

@zedub.zed_cmd(pattern="اتصل$")
async def call(event):
    if event.fwd_from:
        return
    animation_interval = 2
    animation_ttl = range(18)
    zdd = await edit_or_reply(event, "📞")
    await asyncio.sleep(animation_interval)
    animation_chars = [
        "**- جاري الاتصال ...**",
        "**- تم الاتصال.**",
        "**- تيليجرام : مرحبًا، هنا مقر شركة تيليجرام. من معي؟**",
        f"**- أنا: معكم {DEFAULTUSER}، أريد التحدث مع بافل دوروف.**",
        "**- المستخدم مُصرّح له.**",
        "**- جاري الاتصال ببافل دوروف على الرقم +916969696969**",
        "**- تم الاتصال...**",
        "**- أنا: مرحبًا سيدي، الرجاء حظر هذا الشخص.**",
        "**- بافل دوروف: من معي؟**",
        f"**- أنا: {DEFAULTUSER} يا صاح.**",
        "**- بافل دوروف: يا إلهي!!! لم نرك منذ وقت طويل، كيف حالك يا صديقي...\nسأتأكد من حظر حساب ذلك الشخص خلال 24 ساعة.**",
        "**- أنا: شكرًا، أراك لاحقًا.**",
        "**- بافل دوروف: لا داعي للشكر يا صديقي، تيليجرام لنا. فقط اتصل بي عندما تكون متفرغًا.**",
        "**- أنا: هل هناك مشكلة أو حالة طارئة؟**",
        "**- بافل دوروف: نعم يا سيدي، هناك خطأ في تيليجرام إصدار 69.6.9.\nأنا غير قادر على إصلاحه. إذا أمكن، الرجاء المساعدة في إصلاح الخلل.**",
        "**- أنا: أرسل لي التطبيق على حسابي في تيليجرام، سأقوم بإصلاح الخلل وإرساله لك.**",
        "**- بافل دوروف: بالتأكيد يا سيدي، شكرًا لك وداعًا.**",
        "**- تم إنهاء المكالمة الخاصة.**",
    ]
    for i in animation_ttl:
        await zdd.edit(animation_chars[i % 18])
        await asyncio.sleep(animation_interval)

@zedub.zed_cmd(pattern="قتل$")
async def kill(event):
    if event.fwd_from:
        return
    animation_interval = 0.4
    animation_ttl = range(12)
    zdd = await edit_or_reply(event, "...")
    animation_chars = [
        "**تم العثور على الهدف**",
        "**...جارِ إطلاق النار**",
        "**💥...**",
        "**تمت الإصابة ✔️**",
        "**الضحية:** [user](tg://user?id=1)",
        "**القاتل:** أنت",
        "**النتيجة:** مات ☠️",
        "**الناجي:** أنت 😎",
        "**الخاسر:** الضحية 😂",
        "**الرابح:** أنت 🤪",
        "**تمت المهمة بنجاح!**",
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zdd.edit(animation_chars[i % 11])

@zedub.zed_cmd(pattern="انميشن(?: |$)(.*)")
async def anm(event):
    await edit_or_reply(event, """**- قائمــة اوامــر الانميشن 🎆🏖**
⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆
**⎞𝟏⎝** `.غبي`
**لـ الاشاراة الـى ان الشخـص غبـي**

**⎞𝟐⎝**`.قنابل`
**لـ رمـي قنبلـه عـلى الشخـص**

**⎞𝟑⎝** `.اتصل`
**لـ الاتصـال بـ بافـل**

**⎞𝟒⎝** `.قتل`
**لـ قتـل الشخـص**
 
**⎞5⎝** `.شحن`
**لـ شحـن الهـاتف**
 
**⎞6⎝** `.طوبه`
**لعبـة طوبـه**

**⎞7⎝** `.شطرنج`
**لعبـة شطرنج**

**⎞8⎝** `.حلويات`
**لـ عرض الحلويـات**
 
**⎞9⎝** `.جانجست`
**انـا الاقـوى**

**⎞10⎝** `.شنو`
**لـ التعجـب**
 
 𓆩 [𝙎𝙊𝙐𝙍𝘾𝞝 𝙎𝞝𝙍𝙊𝙐𝙅](t.me/KKC8C) 𓆪""")