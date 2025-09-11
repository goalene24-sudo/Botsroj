import time
import random
from datetime import datetime, timedelta
from telethon import events
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import DBSession
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import check_activation, add_points, get_user_rank, Ranks, get_rank_name
from .admin import get_or_create_user


@client.on(events.NewMessage(pattern="^سجلي$"))
async def my_stats_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    sender = await event.get_sender()
    
    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}
        
        married_to = inventory.get("married_to")
        best_friend = inventory.get("best_friend")
        gifted_points = inventory.get("gifted_points", 0)
        
        title = None
        custom_title_item = inventory.get("تخصيص لقب")
        if custom_title_item and time.time() - custom_title_item.get("purchase_time", 0) < custom_title_item.get("duration_days", 0) * 86400:
            title = user_obj.custom_title

        if not title:
            vip_item = inventory.get("لقب vip")
            if vip_item and time.time() - vip_item.get("purchase_time", 0) < vip_item.get("duration_days", 0) * 86400:
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

    if user_obj.join_date:
        profile_text += f"**📅 تاريخ الانضمام:** {user_obj.join_date}\n"
        
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

    if sender.id == receiver.id:
        return await event.reply("**ما يصير تهدي نقاط لنفسك!**")

    try:
        amount = int(event.pattern_match.group(1))
        if amount <= 0:
            return await event.reply("**لازم تهدي عدد نقاط صحيح أكبر من صفر.**")
    except (ValueError, IndexError):
        return await event.reply("**الأمر غلط. اكتب `اهداء` وبعدها عدد النقاط.**")

    async with DBSession() as session:
        sender_obj = await get_or_create_user(session, event.chat_id, sender.id)
        
        if sender_obj.points < amount:
            return await event.reply(f"**مع الأسف، ما عندك نقاط كافية. نقاطك الحالية: {sender_obj.points}**")

        # دوال add_points تتعامل مع الجلسات الخاصة بها
        await add_points(event.chat_id, sender.id, -amount)
        await add_points(event.chat_id, receiver.id, amount)
        
        # تحديث النقاط المهدَاة
        sender_inventory = sender_obj.inventory or {}
        sender_inventory["gifted_points"] = sender_inventory.get("gifted_points", 0) + amount
        sender_obj.inventory = sender_inventory
        flag_modified(sender_obj, "inventory")
        await session.commit()

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
    cooldown = 24 * 60 * 60
    current_time = int(time.time())
    
    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}
        last_reward_time = inventory.get("last_reward", 0)
        
        if current_time - last_reward_time < cooldown:
            remaining_seconds = cooldown - (current_time - last_reward_time)
            remaining_time = str(timedelta(seconds=remaining_seconds)).split('.')[0]
            return await event.reply(f"**ما تستلم راتبك بعد! تعال باچر. 😅\n\nالوقت المتبقي: {remaining_time}**")

        reward = random.randint(100, 500)
        await add_points(event.chat_id, sender.id, reward)
        
        inventory["last_reward"] = current_time
        user_obj.inventory = inventory
        flag_modified(user_obj, "inventory")
        await session.commit()
    
    await event.reply(f"**🎉 استلمت راتبك اليومي! 🎉**\n\n**تمت إضافة {reward} نقطة إلى رصيدك. تعال باچر حتى تستلم بعد!**")


@client.on(events.NewMessage(pattern=r"^ضع نبذة(?: (.*))?$"))
async def set_bio_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    bio_text = event.pattern_match.group(1)
    
    if not bio_text:
        return await event.reply("**لازم تكتب نبذة بعد الأمر.\nمثال: `ضع نبذة مطور البوت`**")
        
    if len(bio_text) > 70:
        return await event.reply("**النبذة طويلة جداً! لازم تكون أقل من 70 حرف.**")

    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, event.sender_id)
        user_obj.bio = bio_text
        await session.commit()
    
    await event.reply("**✅ تم حفظ نبذتك بنجاح. ستظهر الآن في ملفك الشخصي عند استخدام أمر `ايدي`.**")


@client.on(events.NewMessage(pattern="^طلاق$"))
async def divorce_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    
    async with DBSession() as session:
        sender_obj = await get_or_create_user(session, event.chat_id, sender.id)
        sender_inventory = sender_obj.inventory or {}
        married_to = sender_inventory.get("married_to")
        
        if not married_to:
            return await event.reply("**انت أصلاً أعزب/عزباء، منو تطلگ؟ 😂**")
            
        partner_id = married_to.get("id")
        partner_name = married_to.get("name")
        
        # حذف بيانات الزواج من الطرف الأول
        del sender_inventory["married_to"]
        sender_obj.inventory = sender_inventory
        flag_modified(sender_obj, "inventory")
        
        # حذف بيانات الزواج من الطرف الثاني
        partner_obj = await get_or_create_user(session, event.chat_id, partner_id)
        partner_inventory = partner_obj.inventory or {}
        if "married_to" in partner_inventory:
            del partner_inventory["married_to"]
            partner_obj.inventory = partner_inventory
            flag_modified(partner_obj, "inventory")
            
        await session.commit()
    
    await event.reply(f"**💔 تم الطلاق رسمياً!**\n\n**انفصل [{sender.first_name}](tg://user?id={sender.id}) عن [{partner_name}](tg://user?id={partner_id}). كلمن راح بطريقه.**")


@client.on(events.NewMessage(pattern="^ممتلكاتي$"))
async def my_inventory_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    
    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}

    if not inventory:
        return await event.reply("**حقيبة ممتلكاتك فارغة! قم بشراء بعض الأغراض من `المتجر`.**")

    active_items = []
    current_time = int(time.time())

    for item_name, data in inventory.items():
        if not isinstance(data, dict): continue # تجاهل البيانات غير الصالحة
        
        duration_days = data.get("duration_days")
        if duration_days is None: continue

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
    
    date_str = event.pattern_match.group(1).strip()
    
    try:
        day, month = map(int, date_str.replace('/', '-').split('-'))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            raise ValueError("Invalid day or month")
        datetime(year=2024, month=month, day=day) # للتحقق من صحة التاريخ
    except (ValueError, IndexError):
        return await event.reply(
            "**الصيغة غلط! ❌**\n"
            "**لازم تكتب ميلادك بهاي الطريقة (يوم-شهر).**\n"
            "**مثال:** `ضع ميلادي 25-12`"
        )

    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, event.sender_id)
        inventory = user_obj.inventory or {}
        inventory["birthday"] = {"day": day, "month": month}
        user_obj.inventory = inventory
        flag_modified(user_obj, "inventory")
        await session.commit()
    
    await event.reply(f"**✅ تم حفظ تاريخ ميلادك بنجاح:** `{day}-{month}`")


@client.on(events.NewMessage(pattern="^نقاطي$"))
async def my_points_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    
    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        points = user_obj.points
    
    await event.reply(f"**💰 نقاطك الحالية يا [{sender.first_name}](tg://user?id={sender.id}) هي:** `{points}` **نقطة.**")


@client.on(events.NewMessage(pattern="^صديقي المفضل$"))
async def set_best_friend_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    reply = await event.get_reply_message()
    if not reply:
        return await event.reply("**لازم ترد على رسالة الشخص اللي تريد تختاره كصديقك المفضل.**")
        
    sender = await event.get_sender()
    bff = await reply.get_sender()
    
    if sender.id == bff.id:
        return await event.reply("**ما يصير تختار نفسك! 😂**")
        
    if bff.bot:
        return await event.reply("**لا يمكنك اختيار بوت كصديقك المفضل.**")
        
    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}
        inventory["best_friend"] = {"id": bff.id, "name": bff.first_name}
        user_obj.inventory = inventory
        flag_modified(user_obj, "inventory")
        await session.commit()
    
    await event.reply(
        f"**💖 صداقة جديدة! 💖**\n\n"
        f"**أعلن [{sender.first_name}](tg://user?id={sender.id}) أن [{bff.first_name}](tg://user?id={bff.id}) هو صديقه المفضل!**"
    )


@client.on(events.NewMessage(pattern="^حذف صديقي المفضل$"))
async def delete_best_friend_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    
    async with DBSession() as session:
        user_obj = await get_or_create_user(session, event.chat_id, sender.id)
        inventory = user_obj.inventory or {}
        
        if "best_friend" in inventory:
            bff_name = inventory["best_friend"].get("name", "صديقك")
            del inventory["best_friend"]
            user_obj.inventory = inventory
            flag_modified(user_obj, "inventory")
            await session.commit()
            await event.reply(f"**🗑️ تم حذف {bff_name} من قائمة أصدقائك المفضلين.**")
        else:
            await event.reply("**ليس لديك صديق مفضل معين لتقوم بحذفه.**")


@client.on(events.NewMessage(pattern=r"^\.?رتبتي$"))
async def my_rank_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    rank_level = await get_user_rank(event.sender_id, event.chat_id)
    rank_name = get_rank_name(rank_level)
    
    rank_emoji_map = {
        Ranks.MAIN_DEV: "👨‍💻", Ranks.SECONDARY_DEV: "🛠️", Ranks.OWNER: "👑",
        Ranks.CREATOR: "⚜️", Ranks.ADMIN: "🤖", Ranks.MOD: "🛡️",
        Ranks.VIP: "✨", Ranks.MEMBER: "👤"
    }
    emoji = rank_emoji_map.get(rank_level, "👤")
    
    await event.reply(f"⌔︙**رتبتك هي :** {rank_name} {emoji}")


@client.on(events.NewMessage(pattern="^صلاحياتي$"))
async def my_permissions_handler(event):
    if event.is_private or not await check_activation(event.chat_id): return
    
    sender = await event.get_sender()
    
    rank_level = await get_user_rank(sender.id, event.chat_id)
    rank_name = get_rank_name(rank_level)

    if rank_level >= Ranks.ADMIN:
        permissions_text = (
            f"**⚜️ | صلاحياتك يا [{sender.first_name}](tg://user?id={sender.id}):**\n\n"
            f"**رتبتك هي:** `{rank_name}`\n\n"
            "**بصفتك بهذه الرتبة، لديك صلاحية استخدام أوامر الإدارة العليا الخاصة بالبوت.**"
        )
        return await event.reply(permissions_text)

    if rank_level == Ranks.MOD:
        try:
            participant = await client.get_permissions(event.chat_id, sender.id)
            if not hasattr(participant, 'admin_rights') or not participant.admin_rights:
                return await event.reply(f"**رتبتك هي `{rank_name}`، لكن لا يمكنني قراءة صلاحياتك المحددة في المجموعة.**")
            
            perms = participant.admin_rights
            PERMISSIONS_MAP = {
                "change_info": "تغيير معلومات المجموعة", "delete_messages": "حذف الرسائل",
                "ban_users": "حظر/طرد المستخدمين", "invite_users": "دعوة مستخدمين جدد",
                "pin_messages": "تثبيت الرسائل", "add_admins": "إضافة مشرفين جدد",
                "manage_call": "إدارة المحادثات الصوتية"
            }
            
            permissions_text = f"**⚜️ | صلاحياتك كمشرف يا [{sender.first_name}](tg://user?id={sender.id}):**\n\n"
            
            # This part for anonymous admins might need adjustment based on telethon version
            if hasattr(participant, 'participant') and hasattr(participant.participant, 'anonymous') and participant.participant.anonymous:
                permissions_text += "✅ **إرسال الرسائل كمشرف مخفي**\n"
            
            for key, description in PERMISSIONS_MAP.items():
                if getattr(perms, key, False):
                    permissions_text += f"✅ **{description}**\n"
                else:
                    permissions_text += f"❌ **{description}**\n"
            
            return await event.reply(permissions_text)
        except Exception:
             return await event.reply(f"**رتبتك هي `{rank_name}`، لكن حدث خطأ أثناء محاولة قراءة صلاحياتك.**")

    await event.reply("**ليس لديك أي صلاحيات إدارية خاصة في هذه المجموعة.**")
