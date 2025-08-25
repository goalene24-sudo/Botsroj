# plugins/profile.py
import time
import random
from datetime import datetime, timedelta
from telethon import events
from bot import client
from .utils import check_activation, db, add_points, save_db, get_user_rank, Ranks

@client.on(events.NewMessage(pattern="^سجلي$"))
async def my_stats_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    points = user_data.get("points", 0)
    msg_count = user_data.get("msg_count", 0)
    bio = user_data.get("bio")
    join_date = user_data.get("join_date")
    gifted_points = user_data.get("gifted_points", 0)
    married_to = user_data.get("married_to")
    best_friend = user_data.get("best_friend")
    
    inventory = user_data.get("inventory", {})
    title = None

    custom_title_item = inventory.get("تخصيص لقب")
    if custom_title_item:
        purchase_time = custom_title_item.get("purchase_time", 0)
        duration_seconds = custom_title_item.get("duration_days", 0) * 86400
        if time.time() - purchase_time < duration_seconds:
            title = user_data.get("custom_title")

    if not title:
        vip_item = inventory.get("لقب vip")
        if vip_item:
            purchase_time = vip_item.get("purchase_time", 0)
            duration_seconds = vip_item.get("duration_days", 0) * 86400
            if time.time() - purchase_time < duration_seconds:
                title = "عضو مميز 🎖️"

    profile_text = f"**📈 سجلك الشخصي يا [{sender.first_name}](tg://user?id={sender.id})**\n\n"
    
    if married_to:
        partner_id = married_to.get("id")
        partner_name = married_to.get("name")
        profile_text += f"**❤️ الحالة الاجتماعية:** مرتبط/ة بـ [{partner_name}](tg://user?id={partner_id})\n"
    else:
        profile_text += "**❤️ الحالة الاجتماعية:** أعزب/عزباء\n"

    if best_friend:
        bff_id = best_friend.get("id")
        bff_name = best_friend.get("name")
        profile_text += f"**🫂 الصديق المفضل:** [{bff_name}](tg://user?id={bff_id})\n"

    if join_date:
        profile_text += f"**📅 تاريخ الانضمام:** {join_date}\n"
        
    if title:
        profile_text += f"**🎖️ اللقب:** {title}\n"
        
    profile_text += (
        f"**🎁 النقاط المهدَاة:** {gifted_points}\n\n"
        "**استمر بالتفاعل! ✨**"
    )
    
    await event.reply(profile_text)

@client.on(events.NewMessage(pattern=r"^اهداء (\d+)$"))
async def gift_points_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("**لازم ترد على رسالة الشخص اللي تريد تهديه نقاط.**")
    
    sender = await event.get_sender()
    receiver = await reply.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)

    if sender.id == receiver.id:
        return await event.reply("**ما يصير تهدي نقاط لنفسك!**")

    try:
        amount = int(event.pattern_match.group(1))
        if amount <= 0:
            return await event.reply("**لازم تهدي عدد نقاط صحيح أكبر من صفر.**")
    except (ValueError, IndexError):
        return await event.reply("**الأمر غلط. اكتب `اهداء` وبعدها عدد النقاط.**")

    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    sender_points = user_data.get("points", 0)

    if sender_points < amount:
        return await event.reply(f"**مع الأسف، ما عندك نقاط كافية. نقاطك الحالية: {sender_points}**")

    add_points(event.chat_id, sender.id, -amount)
    add_points(event.chat_id, receiver.id, amount)
    
    user_data["gifted_points"] = user_data.get("gifted_points", 0) + amount
    db[chat_id_str]["users"][user_id_str] = user_data
    save_db(db)

    await event.reply(
        f"**🎁 تمت الهدية بنجاح!**\n\n"
        f"**المهدي:** [{sender.first_name}](tg://user?id={sender.id})\n"
        f"**المستلم:** [{receiver.first_name}](tg://user?id={receiver.id})\n"
        f"**المبلغ:** `{amount}` **نقطة.**"
    )

@client.on(events.NewMessage(pattern="^راتب$"))
async def daily_reward_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    last_reward_time = user_data.get("last_reward", 0)
    current_time = int(time.time())
    
    cooldown = 24 * 60 * 60 

    if current_time - last_reward_time < cooldown:
        remaining_seconds = cooldown - (current_time - last_reward_time)
        remaining_time = str(timedelta(seconds=remaining_seconds)).split('.')[0]
        return await event.reply(f"**ما تستلم راتبك بعد! تعال باچر. 😅\n\نالوقت المتبقي: {remaining_time}**")

    reward = random.randint(100, 500)
    add_points(event.chat_id, sender.id, reward)
    
    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    user_db.setdefault(user_id_str, {})["last_reward"] = current_time
    save_db(db)
    
    await event.reply(f"**🎉 استلمت راتبك اليومي! 🎉**\n\n**تمت إضافة {reward} نقطة إلى رصيدك. تعال باچر حتى تستلم بعد!**")

@client.on(events.NewMessage(pattern=r"^ضع نبذة(?: (.*))?$"))
async def set_bio_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
        
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    bio_text = event.pattern_match.group(1)
    
    if not bio_text:
        return await event.reply("**لازم تكتب نبذة بعد الأمر.\nمثال: `ضع نبذة مطور البوت`**")
        
    if len(bio_text) > 70:
        return await event.reply("**النبذة طويلة جداً! لازم تكون أقل من 70 حرف.**")

    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    user_db.setdefault(user_id_str, {})["bio"] = bio_text
    save_db(db)
    
    await event.reply("**✅ تم حفظ نبذتك بنجاح. ستظهر الآن في ملفك الشخصي عند استخدام أمر `ايدي`.**")

@client.on(events.NewMessage(pattern="^طلاق$"))
async def divorce_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    married_to = user_data.get("married_to")
    
    if not married_to:
        return await event.reply("**انت أصلاً أعزب/عزباء، منو تطلگ؟ 😂**")
        
    partner_id = married_to.get("id")
    partner_name = married_to.get("name")
    partner_id_str = str(partner_id)
    
    del db[chat_id_str]["users"][user_id_str]["married_to"]
    if partner_id_str in db[chat_id_str]["users"] and "married_to" in db[chat_id_str]["users"][partner_id_str]:
        del db[chat_id_str]["users"][partner_id_str]["married_to"]
    
    save_db(db)
    
    await event.reply(f"**💔 تم الطلاق رسمياً!**\n\n**انفصل [{sender.first_name}](tg://user?id={sender.id}) عن [{partner_name}](tg://user?id={partner_id}). كلمن راح بطريقه.**")

@client.on(events.NewMessage(pattern="^ممتلكاتي$"))
async def my_inventory_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)

    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    inventory = user_data.get("inventory", {})

    if not inventory:
        return await event.reply("**حقيبة ممتلكاتك فارغة! قم بشراء بعض الأغراض من `المتجر`.**")

    active_items = []
    current_time = int(time.time())

    for item_name, data in inventory.items():
        duration_days = data.get("duration_days")
        if duration_days is None:
            continue

        purchase_time = data.get("purchase_time", 0)
        duration_seconds = duration_days * 86400
        time_elapsed = current_time - purchase_time

        if time_elapsed < duration_seconds:
            remaining_seconds = duration_seconds - time_elapsed
            td = timedelta(seconds=int(remaining_seconds))
            days, hours, minutes = td.days, td.seconds // 3600, (td.seconds // 60) % 60
            
            parts = []
            if days > 0: parts.append(f"{days} أيام")
            if hours > 0: parts.append(f"{hours} ساعات")
            if minutes > 0: parts.append(f"{minutes} دقائق")
            
            remaining_time_ar = " و ".join(parts) if parts else "أقل من دقيقة"
            active_items.append(f"▫️ **{item_name.title()}**: يتبقى `{remaining_time_ar}`")

    if not active_items:
        return await event.reply("**ليس لديك أي امتيازات فعالة حالياً.**")

    inventory_text = f"**🎒 ممتلكاتك الفعالة يا [{sender.first_name}](tg://user?id={sender.id})**\n\n"
    inventory_text += "\n".join(active_items)

    await event.reply(inventory_text)

@client.on(events.NewMessage(pattern=r"^ضع ميلادي (.*)$"))
async def set_birthday_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
        
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    date_str = event.pattern_match.group(1).strip()
    
    try:
        day, month = map(int, date_str.replace('/', '-').split('-'))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            raise ValueError("Invalid day or month")
        datetime(year=2024, month=month, day=day)
    except (ValueError, IndexError):
        return await event.reply(
            "**الصيغة غلط! ❌**\n"
            "**لازم تكتب ميلادك بهاي الطريقة (يوم-شهر).**\n"
            "**مثال:** `ضع ميلادي 25-12`"
        )

    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    user_db.setdefault(user_id_str, {})["birthday"] = {"day": day, "month": month}
    save_db(db)
    
    await event.reply(f"**✅ تم حفظ تاريخ ميلادك بنجاح:** `{day}-{month}`")

@client.on(events.NewMessage(pattern="^نقاطي$"))
async def my_points_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    points = user_data.get("points", 0)
    
    await event.reply(f"**💰 نقاطك الحالية يا [{sender.first_name}](tg://user?id={sender.id}) هي:** `{points}` **نقطة.**")

@client.on(events.NewMessage(pattern="^صديقي المفضل$"))
async def set_best_friend_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    reply = await event.get_reply_message()
    if not reply:
        return await event.reply("**لازم ترد على رسالة الشخص اللي تريد تختاره كصديقك المفضل.**")
        
    sender = await event.get_sender()
    bff = await reply.get_sender()
    chat_id_str, sender_id_str = str(event.chat_id), str(sender.id)
    
    if sender.id == bff.id:
        return await event.reply("**ما يصير تختار نفسك! 😂**")
        
    if bff.bot:
        return await event.reply("**لا يمكنك اختيار بوت كصديقك المفضل.**")
        
    user_db = db.setdefault(chat_id_str, {}).setdefault("users", {})
    sender_data = user_db.setdefault(sender_id_str, {})
    
    sender_data["best_friend"] = {"id": bff.id, "name": bff.first_name}
    save_db(db)
    
    await event.reply(
        f"**💖 صداقة جديدة! 💖**\n\n"
        f"**أعلن [{sender.first_name}](tg://user?id={sender.id}) أن [{bff.first_name}](tg://user?id={bff.id}) هو صديقه المفضل!**"
    )

@client.on(events.NewMessage(pattern="^حذف صديقي المفضل$"))
async def delete_best_friend_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
        
    sender = await event.get_sender()
    chat_id_str, user_id_str = str(event.chat_id), str(sender.id)
    
    user_data = db.get(chat_id_str, {}).get("users", {}).get(user_id_str, {})
    
    if "best_friend" in user_data:
        bff_name = user_data["best_friend"].get("name", "صديقك")
        del db[chat_id_str]["users"][user_id_str]["best_friend"]
        save_db(db)
        await event.reply(f"**🗑️ تم حذف {bff_name} من قائمة أصدقائك المفضلين.**")
    else:
        await event.reply("**ليس لديك صديق مفضل معين لتقوم بحذفه.**")

@client.on(events.NewMessage(pattern=r"^\.?رتبتي$"))
async def my_rank_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    rank_int = await get_user_rank(event.sender_id, event)

    rank_map = {
        Ranks.DEVELOPER: "المطور 👨‍💻",
        Ranks.OWNER: "مالك المجموعة 👑",
        Ranks.CREATOR: "منشئ في البوت ⚜️",
        Ranks.BOT_ADMIN: "ادمن في البوت 🤖",
        Ranks.GROUP_ADMIN: "مشرف في المجموعة 🛡️",
        Ranks.MEMBER: "عضو فقط 👤"
    }
    
    rank_ar = rank_map.get(rank_int, "عضو فقط 👤")
    
    await event.reply(f"⌔︙**رتبتك هي :** {rank_ar}")
