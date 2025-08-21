# plugins/shop.py
import time
from telethon import events
from bot import client
import config
from .utils import check_activation, db, add_points, save_db

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

@client.on(events.NewMessage(pattern="^المتجر$"))
async def shop_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    shop_text = "🛒 **متجر سُـرُوچ** 🛒\n\nأهلاً بك في المتجر! هنا يمكنك إنفاق نقاطك لشراء امتيازات رائعة.\n\n"
    
    for item_name, details in SHOP_ITEMS.items():
        shop_text += f"▫️ **{item_name.title()}**\n"
        shop_text += f"   - **السعر:** `{details['price']}` نقطة\n"
        shop_text += f"   - **الوصف:** {details['description']}\n\n"
        
    shop_text += "**للشراء:** `شراء [اسم الغرض]`\n**للقب المخصص:** `ضع لقبي [اللقب]`"
    shop_text += "\n\n**🏦 أوامر البنك:** `ايداع`, `سحب`, `رصيدي بالبنك`"
    
    await event.reply(shop_text)

@client.on(events.NewMessage(pattern=r"^شراء (.+)"))
async def buy_item_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    item_name_to_buy = event.pattern_match.group(1).strip().lower()
    
    if item_name_to_buy not in SHOP_ITEMS:
        return await event.reply(f"عذراً، الغرض '{item_name_to_buy}' غير موجود في المتجر. تأكد من كتابة الاسم بالضبط كما هو في قائمة `المتجر`.")
        
    item_details = SHOP_ITEMS[item_name_to_buy]
    price = item_details["price"]
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    user_points = user_data.get("points", 0)
    
    is_developer = sender.id in config.SUDO_USERS

    if not is_developer and user_points < price:
        return await event.reply(f"عذراً، نقاطك غير كافية! 😢\n- سعر هذا الغرض: **{price}**\n- نقاطك الحالية: **{user_points}**")
        
    if item_name_to_buy == "تذكرة يانصيب":
        if not is_developer:
            add_points(event.chat_id, sender.id, -price)
        
        if "lottery_players" not in db.get(chat_id_str, {}):
            db.setdefault(chat_id_str, {})["lottery_players"] = []
            
        db[chat_id_str]["lottery_players"].append(user_id_str)
        save_db(db)
        
        total_tickets = len(db[chat_id_str]["lottery_players"])
        return await event.reply(f"**🎟️ تم شراء تذكرة يانصيب بنجاح!**\n\nحظاً موفقاً في السحب القادم. إجمالي عدد التذاكر المباعة حتى الآن: **{total_tickets}** تذكرة.")

    inventory = user_data.get("inventory", {})
    if item_name_to_buy in inventory:
        purchase_time = inventory[item_name_to_buy].get("purchase_time", 0)
        duration_seconds = inventory[item_name_to_buy].get("duration_days", 0) * 24 * 60 * 60
        if time.time() - purchase_time < duration_seconds:
            return await event.reply("لديك هذا الامتياز فعالاً بالفعل! انتظر حتى ينتهي لتتمكن من شرائه مجدداً.")
            
    if not is_developer:
        add_points(event.chat_id, sender.id, -price)
    
    purchase_timestamp = int(time.time())
    
    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    inventory_db = user_db.setdefault(user_id_str, {}).setdefault("inventory", {})
    inventory_db[item_name_to_buy] = {
        "purchase_time": purchase_timestamp,
        "duration_days": item_details["duration_days"]
    }
    save_db(db)
    
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
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    inventory = user_data.get("inventory", {})
    
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
        
    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    user_db.setdefault(user_id_str, {})["custom_title"] = custom_title
    save_db(db)
    
    await event.reply(f"**✅ تم وضع لقبك المخصص بنجاح إلى:** `{custom_title}`")

# --- أوامر البنك ---
@client.on(events.NewMessage(pattern=r"^ايداع (\d+)$"))
async def deposit_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    amount = int(event.pattern_match.group(1))

    if amount <= 0:
        return await event.reply("**لازم تودع مبلغ أكبر من صفر.**")

    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    user_points = user_data.get("points", 0)

    if user_points < amount:
        return await event.reply(f"**ما عندك نقاط كافية للإيداع. رصيدك الحالي: {user_points}**")

    # خصم النقاط من الرصيد العام وإضافتها للبنك
    add_points(event.chat_id, sender.id, -amount)
    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    user_data = user_db.setdefault(user_id_str, {})
    user_data["bank_balance"] = user_data.get("bank_balance", 0) + amount
    save_db(db)

    await event.reply(f"**💰 تم إيداع `{amount}` نقطة في حسابك البنكي بنجاح.**\n**رصيدك في البنك الآن:** `{user_data['bank_balance']}`")

@client.on(events.NewMessage(pattern=r"^سحب (\d+)$"))
async def withdraw_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
        
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    amount = int(event.pattern_match.group(1))

    if amount <= 0:
        return await event.reply("**لازم تسحب مبلغ أكبر من صفر.**")
        
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    bank_balance = user_data.get("bank_balance", 0)
    
    if bank_balance < amount:
        return await event.reply(f"**رصيدك في البنك غير كافٍ. رصيدك البنكي: {bank_balance}**")

    # خصم النقاط من البنك وإضافتها للرصيد العام
    user_data["bank_balance"] -= amount
    add_points(event.chat_id, sender.id, amount)
    save_db(db)

    await event.reply(f"**💸 تم سحب `{amount}` نقطة من حسابك البنكي بنجاح.**\n**رصيدك في البنك الآن:** `{user_data['bank_balance']}`")

@client.on(events.NewMessage(pattern="^رصيدي بالبنك$"))
async def bank_balance_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return

    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)

    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    user_data = user_db.setdefault(user_id_str, {})

    bank_balance = user_data.get("bank_balance", 0)
    last_interest_time = user_data.get("last_interest_time", int(time.time()))
    
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
        
        user_data["bank_balance"] = bank_balance
        user_data["last_interest_time"] = last_interest_time + periods_passed * interest_period
        save_db(db)

    text = f"**🏦 رصيدك في بنك سُـرُوچ**\n\n**- الرصيد الحالي:** `{bank_balance}` نقطة.\n"
    if interest_earned > 0:
        text += f"**- الأرباح المضافة الآن:** `{interest_earned}` نقطة (بنسبة 1% يومياً).\n"
    text += "\n**استثمر نقاطك لتربح المزيد!**"
    
    await event.reply(text)
