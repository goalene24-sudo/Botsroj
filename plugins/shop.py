import time
import asyncio
from telethon import events
from sqlalchemy.orm.attributes import flag_modified

from bot import client
import config
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, add_points
# (ملاحظة: get_or_create_user موجودة في utils، لذا تم تبسيط الاستيراد)
from .utils import get_or_create_user, get_or_create_chat


# تعريف أغراض المتجر
SHOP_ITEMS = {
    "لقب vip": {
        "price": 10000,
        "description": "🎖️ | احصل على لقب VIP مميز يظهر في ملفك الشخصي لمدة 7 أيام.",
        "duration_days": 7
    },
    "تخصيص لقب": {
        "price": 20000,
        "description": "✏️ | ضع لقباً مخصصاً من اختيارك يظهر في ملفك الشخصي لمدة 30 يوماً.",
        "duration_days": 30
    },
    "مضاعف نقاط": {
        "price": 5000,
        "description": "🔥 | ضاعف النقاط التي تكتسبها من كل رسالة (x2) لمدة 24 ساعة.",
        "duration_days": 1
    },
    "تذكرة يانصيب": {
        "price": 200,
        "description": "🎟️ | ادخل السحب على جائزة كبرى من النقاط! كلما اشتريت تذاكر أكثر، زادت فرصتك بالربح.",
        "duration_days": None # لا يوجد مدة صلاحية لهذا الغرض
    },
    "زخرفة": {
        "price": 7500,
        "description": "✨ | اشترِ وساماً يظهر بجانب اسمك في بطاقة الأيدي ليميزك عن الآخرين (لمدة 15 يوماً).",
        "duration_days": 15
    },
    "حصانة": {
        "price": 2500,
        "description": "🛡️ | اشترِ درع حصانة يمنع الآخرين من استخدام الأفعال التفاعلية ضدك (مثل صفعة) لمدة 24 ساعة.",
        "duration_days": 1
    }
}

@client.on(events.NewMessage(pattern=r"^شراء (.+)"))
async def buy_item_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    item_name_to_buy = event.pattern_match.group(1).strip().lower()
    
    if item_name_to_buy not in SHOP_ITEMS:
        return await event.reply(f"عذراً، الغرض '{item_name_to_buy}' غير موجود في المتجر. تأكد من كتابة الاسم بالضبط كما هو في قائمة `المتجر`.")
        
    item_details = SHOP_ITEMS[item_name_to_buy]
    price = item_details["price"]
    is_developer = sender.id in config.SUDO_USERS

    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)

        if not is_developer and user_obj.points < price:
            return await event.reply(f"عذراً، نقاطك غير كافية! 😢\n- سعر هذا الغرض: **{price}**\n- نقاطك الحالية: **{user_obj.points}**")
            
        if item_name_to_buy == "تذكرة يانصيب":
            if not is_developer:
                user_obj.points -= price
            
            chat_obj = await get_or_create_chat(session, event.chat_id)
            settings = chat_obj.settings or {}
            lottery_players = settings.get("lottery_players", [])
            lottery_players.append(str(sender.id))
            settings["lottery_players"] = lottery_players
            chat_obj.settings = settings
            flag_modified(chat_obj, "settings")
            
            await session.commit()
            
            total_tickets = len(lottery_players)
            return await event.reply(f"**🎟️ تم شراء تذكرة يانصيب بنجاح!**\n\nحظاً موفقاً في السحب القادم. إجمالي عدد التذاكر المباعة حتى الآن: **{total_tickets}** تذكرة.")

        inventory = user_obj.inventory or {}
        if item_name_to_buy in inventory:
            purchase_time = inventory[item_name_to_buy].get("purchase_time", 0)
            duration_seconds = inventory[item_name_to_buy].get("duration_days", 0) * 24 * 60 * 60
            if time.time() - purchase_time < duration_seconds:
                return await event.reply("لديك هذا الامتياز فعالاً بالفعل! انتظر حتى ينتهي لتتمكن من شرائه مجدداً.")
                
        if not is_developer:
            user_obj.points -= price
        
        purchase_timestamp = int(time.time())
        
        inventory[item_name_to_buy] = {
            "purchase_time": purchase_timestamp,
            "duration_days": item_details["duration_days"]
        }
        user_obj.inventory = inventory
        flag_modified(user_obj, "inventory")
        
        await session.commit()
    
    success_message = f"✅ **تم شراء '{item_name_to_buy.title()}' بنجاح!**\n\n"
    if not is_developer:
        success_message += f"تم خصم `{price}` نقطة من رصيدك. "
    success_message += "استمتع بالامتياز الجديد!"
    
    if item_name_to_buy == "تخصيص لقب":
        success_message += "\n\n**الآن، استخدم الأمر `ضع لقبي [اللقب الذي تريده]` لوضع لقبك.**"
    
    await event.reply(success_message)


@client.on(events.NewMessage(pattern=r"^ضع لقبي (.+)"))
async def set_custom_title_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    
    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}
        
        item_name = "تخصيص لقب"
        if item_name not in inventory and sender.id not in config.SUDO_USERS:
            return await event.reply(f"**ليس لديك الصلاحية لوضع لقب مخصص. يجب عليك شراء '{item_name}' من `المتجر` أولاً.**")
        
        if sender.id not in config.SUDO_USERS:
            purchase_info = inventory[item_name]
            purchase_time = purchase_info.get("purchase_time", 0)
            duration_days = purchase_info.get("duration_days", 0)
            duration_seconds = duration_days * 24 * 60 * 60
            
            if time.time() - purchase_time > duration_seconds:
                return await event.reply(f"**لقد انتهت صلاحية امتياز '{item_name}' لديك. قم بشرائه مجدداً من `المتجر` لتتمكن من وضع لقب جديد.**")
            
        custom_title = event.pattern_match.group(1).strip()
        
        if len(custom_title) > 20:
            return await event.reply("**عذراً، يجب أن لا يتجاوز اللقب 20 حرفاً.**")
            
        user_obj.custom_title = custom_title
        await session.commit()
    
    await event.reply(f"**✅ تم وضع لقبك المخصص بنجاح إلى:** `{custom_title}`")


# --- أوامر البنك ---
@client.on(events.NewMessage(pattern=r"^ايداع (\d+)$"))
async def deposit_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    sender = await event.get_sender()
    try:
        amount = int(event.pattern_match.group(1))
        if amount <= 0:
            return await event.reply("**لازم تودع مبلغ أكبر من صفر.**")
    except (ValueError, IndexError):
        return await event.reply("**الرجاء إدخال مبلغ صحيح.**")

    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        
        if user_obj.points < amount:
            return await event.reply(f"**ما عندك نقاط كافية للإيداع. رصيدك الحالي: {user_obj.points}**")

        user_obj.points -= amount
        inventory = user_obj.inventory or {}
        inventory["bank_balance"] = inventory.get("bank_balance", 0) + amount
        user_obj.inventory = inventory
        flag_modified(user_obj, "inventory")
        await session.commit()
        
        new_balance = inventory["bank_balance"]

    await event.reply(f"**💰 تم إيداع `{amount}` نقطة في حسابك البنكي بنجاح.**\n**رصيدك في البنك الآن:** `{new_balance}`")


@client.on(events.NewMessage(pattern=r"^سحب (\d+)$"))
async def withdraw_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
        
    sender = await event.get_sender()
    try:
        amount = int(event.pattern_match.group(1))
        if amount <= 0:
            return await event.reply("**لازم تسحب مبلغ أكبر من صفر.**")
    except (ValueError, IndexError):
        return await event.reply("**الرجاء إدخال مبلغ صحيح.**")
        
    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}
        bank_balance = inventory.get("bank_balance", 0)
        
        if bank_balance < amount:
            return await event.reply(f"**رصيدك في البنك غير كافٍ. رصيدك البنكي: {bank_balance}**")

        inventory["bank_balance"] -= amount
        user_obj.points += amount
        user_obj.inventory = inventory
        flag_modified(user_obj, "inventory")
        await session.commit()
        
        new_balance = inventory["bank_balance"]

    await event.reply(f"**💸 تم سحب `{amount}` نقطة من حسابك البنكي بنجاح.**\n**رصيدك في البنك الآن:** `{new_balance}`")


@client.on(events.NewMessage(pattern="^رصيدي بالبنك$"))
async def bank_balance_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    sender = await event.get_sender()
    
    async with AsyncDBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}

        bank_balance = inventory.get("bank_balance", 0)
        last_interest_time = inventory.get("last_interest_time", int(time.time()))
        
        current_time = int(time.time())
        interest_rate = 0.01  # 1% daily interest
        interest_period = 86400  # 24 hours in seconds

        time_diff = current_time - last_interest_time
        interest_earned = 0

        if time_diff >= interest_period and bank_balance > 0:
            periods_passed = time_diff // interest_period
            initial_balance = bank_balance
            for _ in range(periods_passed):
                bank_balance += bank_balance * interest_rate
            
            bank_balance = int(bank_balance)
            interest_earned = bank_balance - initial_balance
            
            inventory["bank_balance"] = bank_balance
            inventory["last_interest_time"] = last_interest_time + periods_passed * interest_period
            user_obj.inventory = inventory
            flag_modified(user_obj, "inventory")
            await session.commit()

    text = f"**🏦 رصيدك في بنك سُـرُوچ**\n\n**- الرصيد الحالي:** `{bank_balance}` نقطة.\n"
    if interest_earned > 0:
        text += f"**- الأرباح المضافة الآن:** `{interest_earned}` نقطة (بنسبة 1% يومياً).\n"
    text += "\n**استثمر نقاطك لتربح المزيد!**"
    
    await event.reply(text)
