# plugins/animations.py
import asyncio
from collections import deque
from telethon import events
from bot import client
from .utils import check_activation

@client.on(events.NewMessage(pattern="^غبي$"))
async def ghabe(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    animation_interval = 0.3
    animation_ttl = range(14)
    zed = await event.reply("🧠.")
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
        await zed.edit(animation_chars[i % 14])

@client.on(events.NewMessage(pattern="^قنابل$"))
async def bomd(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    animation_interval = 0.4
    animation_ttl = range(13)
    zed = await event.reply("💣")
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
        await zed.edit(animation_chars[i % 13])

@client.on(events.NewMessage(pattern="^اتصل$"))
async def call(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    user = await event.get_sender()
    name = user.first_name
    animation_interval = 2
    animation_ttl = range(18)
    zed = await event.reply("📞")
    await asyncio.sleep(animation_interval)
    animation_chars = [
        "**- جاري الاتصال ...**",
        "**- تم الاتصال.**",
        "**- تيليجرام : مرحبًا، هنا مقر شركة تيليجرام. من معي؟**",
        f"**- أنا: معكم {name}، أريد التحدث مع بافل دوروف.**",
        "**- المستخدم مُصرّح له.**",
        "**- جاري الاتصال ببافل دوروف على الرقم +916969696969**",
        "**- تم الاتصال...**",
        "**- أنا: مرحبًا سيدي، الرجاء حظر هذا الشخص.**",
        "**- بافل دوروف: من معي؟**",
        f"**- أنا: {name} يا صاح.**",
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
        await zed.edit(animation_chars[i % 18])
        await asyncio.sleep(animation_interval)

@client.on(events.NewMessage(pattern="^قتل$"))
async def kill(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    reply = await event.get_reply_message()
    if not reply:
        return await event.reply("**الرجاء الرد على المستخدم الذي تريد قتله.**")
    
    victim = await event.client.get_entity(reply.sender_id)
    killer = await event.get_sender()
    
    animation_interval = 0.4
    animation_ttl = range(12)
    zed = await event.reply("...")
    animation_chars = [
        f"**تم تحديد الهدف: [{victim.first_name}](tg://user?id={victim.id})**",
        "**...جارِ إطلاق النار**",
        "**💥...**",
        "**تمت الإصابة ✔️**",
        f"**الضحية:** [{victim.first_name}](tg://user?id={victim.id})",
        f"**القاتل:** [{killer.first_name}](tg://user?id={killer.id})",
        "**النتيجة:** مات ☠️",
        "**الناجي:** أنت 😎",
        "**الخاسر:** الضحية 😂",
        "**الرابح:** أنت 🤪",
        "**تمت المهمة بنجاح!**",
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zed.edit(animation_chars[i % 11])

@client.on(events.NewMessage(pattern="^شنو$"))
async def wht(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    animation_interval = 0.8
    animation_ttl = range(5)
    zed = await event.reply("شنو")
    animation_chars = [
        "هاي شنو",
        "هاي شنو هاي",
        "هاي شنو هاي يمعود",
        "هاي شنو هاي يمعود!!",
        "هاي شنو هاي يمعود!!\nhttps://telegra.ph/file/f3b760e4a99340d331f9b.jpg",
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zed.edit(animation_chars[i % 5], link_preview=True)

@client.on(events.NewMessage(pattern="^طوبه$"))
async def toba(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    animation_interval = 0.3
    animation_ttl = range(30)
    zed = await event.reply("طوبة.. طبت.. طوبة.. طبت.. بيك...")
    animation_chars = [
        "🔴⬛⬛⬜⬜\n⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜",
        "⬜⬜⬛⬜⬜\n⬜⬛⬜⬜⬜\n🔴⬜⬜⬜⬜",
        "⬜⬜⬛⬜⬜\n⬜⬜⬛⬜⬜\n⬜⬜🔴⬜⬜",
        "⬜⬜⬛⬜⬜\n⬜⬜⬜⬛⬜\n⬜⬜⬜⬜🔴",
        "⬜⬜⬛⬛🔴\n⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜",
        "⬜⬜⬛⬜⬜\n⬜⬜⬜⬛⬜\n⬜⬜⬜⬜🔴",
        "⬜⬜⬛⬜⬜\n⬜⬜⬛⬜⬜\n⬜⬜🔴⬜⬜",
        "⬜⬜⬛⬜⬜\n⬜⬛⬜⬜⬜\n🔴⬜⬜⬜⬜",
        "🔴⬛⬛⬜⬜\n⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜",
    ]
    await asyncio.sleep(3)
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zed.edit(animation_chars[i % 9])

@client.on(events.NewMessage(pattern="^شطرنج$"))
async def chess(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    animation_interval = 0.3
    animation_ttl = range(15)
    zed = await event.reply("شطرنج....")
    animation_chars = [
        "⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬛⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜",
        "⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬛⬛⬛⬜⬜\n⬜⬜⬛⬜⬛⬜⬜\n⬜⬜⬛⬛⬛⬜⬜\n⬜⬜⬜⬜⬜⬜⬜\n⬜⬜⬜⬜⬜⬜⬜",
        "⬜⬜⬜⬜⬜⬜⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬜⬜⬜⬜⬜⬜",
        "⬛⬛⬛⬛⬛⬛⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬛⬛⬛⬛⬛⬛",
        "⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛",
        "⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛⬜",
        "⬜⬜⬜⬜⬜⬜⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬜⬜⬜⬜⬜⬜",
        "⬛⬛⬛⬛⬛⬛⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬜⬛⬛⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬛⬛⬜⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬛⬛⬛⬛⬛⬛",
        "⬜⬜⬜⬜⬜⬜⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬜⬜⬜⬜⬜⬜",
        "⬛⬛⬛⬛⬛⬛⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬜⬛⬛⬛⬜⬛\n⬛⬜⬛⬜⬛⬜⬛\n⬛⬜⬛⬛⬛⬜⬛\n⬛⬜⬜⬜⬜⬜⬛\n⬛⬛⬛⬛⬛⬛⬛",
        "⬜⬜⬜⬜⬜⬜⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬜⬛⬜⬛⬜\n⬜⬛⬜⬜⬜⬛⬜\n⬜⬛⬛⬛⬛⬛⬜\n⬜⬜⬜⬜⬜⬜⬜",
        "⬛⬛⬛⬛⬛\n⬛⬜⬜⬜⬛\n⬛⬜⬛⬜⬛\n⬛⬜⬜⬜⬛\n⬛⬛⬛⬛⬛",
        "⬜⬜⬜\n⬜⬛⬜\n⬜⬜⬜",
        "🔴",
        "لقد فزت ♚",
    ]
    for i in animation_ttl:
        await asyncio.sleep(animation_interval)
        await zed.edit(animation_chars[i % 15])

@client.on(events.NewMessage(pattern="^حلويات$"))
async def candi(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    zed = await event.reply("🍦")
    deq = deque(list("🍦🍧🍩🍪🎂🍰🧁🍫🍬🍭"))
    for _ in range(30):
        await asyncio.sleep(0.4)
        await zed.edit("".join(deq))
        deq.rotate(1)

@client.on(events.NewMessage(pattern="^جانجست$"))
async def gangasta(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    zed = await event.reply("gangasta")
    await zed.edit("EVERyBOdy")
    await asyncio.sleep(0.3)
    await zed.edit("iZ")
    await asyncio.sleep(0.2)
    await zed.edit("GangSTur")
    await asyncio.sleep(0.5)
    await zed.edit("UNtIL ")
    await asyncio.sleep(0.2)
    await zed.edit("I")
    await asyncio.sleep(0.3)
    await zed.edit("ArRivE")
    await asyncio.sleep(0.3)
    await zed.edit("🔥🔥🔥")
    await asyncio.sleep(0.3)
    await zed.edit("EVERyBOdy iZ GangSTur UNtIL I ArRivE 🔥🔥🔥")

@client.on(events.NewMessage(pattern="^شحن$"))
async def charging(event):
    if not await check_activation(event.chat_id): return
    if event.fwd_from:
        return
    zed = await event.reply("...جارِ الشحن")
    await asyncio.sleep(1)
    await zed.edit("█▒▒▒▒▒▒▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("██▒▒▒▒▒▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("███▒▒▒▒▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("████▒▒▒▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("█████▒▒▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("██████▒▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("███████▒▒▒")
    await asyncio.sleep(1)
    await zed.edit("████████▒▒")
    await asyncio.sleep(1)
    await zed.edit("█████████▒")
    await asyncio.sleep(1)
    await zed.edit("██████████")
    await asyncio.sleep(1)
    await zed.edit("اكتمل الشحن بنجاح ✓")

@client.on(events.NewMessage(pattern="^انميشن$"))
async def anm(event):
    if not await check_activation(event.chat_id): return
    await event.reply("""**- قائمــة اوامــر الانميشن 🎆🏖**
⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆
`غبي`
**لـ الاشاراة الـى ان الشخـص غبـي**

`قنابل`
**لـ رمـي قنبلـه عـلى الشخـص**

`اتصل`
**لـ الاتصـال بـ بافـل**

`قتل`
**لـ قتـل الشخـص**
 
`شحن`
**لـ شحـن الهـاتف**
 
`طوبه`
**لعبـة طوبـه**

`شطرنج`
**لعبـة شطرنج**

`حلويات`
**لـ عرض الحلويـات**
 
`جانجست`
**انـا الاقـوى**

`شنو`
**لـ التعجـب**
""")
