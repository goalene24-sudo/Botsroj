# --- استدعاء الدوال والمتغيرات المشتركة من الملف المساعد ---
from .protection_helpers import *

# --- قسم أوامر القوائم ---

async def list_bot_admins_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            admins_res = await session.execute(select(BotAdmin).where(BotAdmin.chat_id == event.chat_id))
            admins = admins_res.scalars().all()

        if not admins:
            return await event.reply("**ماكو أي ادمن بالبوت حالياً 🤖**")

        text = "**🤖 | قائمة الأدمنية بالبوت:**\n\n"
        for admin in admins:
            try:
                user = await client.get_entity(admin.user_id)
                text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            except:
                text += f"• `{admin.user_id}`\n"
        await event.reply(text)
    except Exception as e:
        logger.error(f"Error in list_bot_admins_logic: {e}", exc_info=True)
        await event.reply("**ماكدرت اجيب قائمة الأدمنية، اكو خطأ صار 😢**")

async def clear_all_bot_admins_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
        if actor_rank < Ranks.OWNER:
            return await event.reply("**بس المالك يكدر يسوي هيج شغلة خطيرة 👑**")

        async with AsyncDBSession() as session:
            await session.execute(delete(BotAdmin).where(BotAdmin.chat_id == event.chat_id))
            await session.commit()

        await event.reply("**🗑️ | تم مسح كل الأدمنية بالبوت.**")
    except Exception as e:
        logger.error(f"Error in clear_all_bot_admins_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسحهم 😢**")

async def list_vips_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            vips_res = await session.execute(select(Vip).where(Vip.chat_id == event.chat_id))
            vips = vips_res.scalars().all()

        if not vips:
            return await event.reply("**ماكو أي عضو مميز حالياً ✨**")

        text = "**✨ | قائمة الأعضاء المميزين:**\n\n"
        for vip in vips:
            try:
                user = await client.get_entity(vip.user_id)
                text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            except:
                text += f"• `{vip.user_id}`\n"
        await event.reply(text)
    except Exception as e:
        logger.error(f"Error in list_vips_logic: {e}", exc_info=True)
        await event.reply("**ماكدرت اجيب قائمة المميزين، اكو خطأ صار 😢**")

async def clear_all_vips_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
        if actor_rank < Ranks.CREATOR:
            return await event.reply("**هاي الشغلة للمنشئين والمالك بس ⚜️**")

        async with AsyncDBSession() as session:
            await session.execute(delete(Vip).where(Vip.chat_id == event.chat_id))
            await session.commit()

        await event.reply("**🗑️ | تم مسح كل الأعضاء المميزين.**")
    except Exception as e:
        logger.error(f"Error in clear_all_vips_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسحهم 😢**")

async def list_creators_logic(event, command_text):
    try:
        async with AsyncDBSession() as session:
            creators_res = await session.execute(select(Creator).where(Creator.chat_id == event.chat_id))
            creators = creators_res.scalars().all()

        if not creators:
            return await event.reply("**ماكو أي منشئ بالكروب حالياً ⚜️**")

        text = "**⚜️ | قائمة المنشئين بالكروب:**\n\n"
        for creator in creators:
            try:
                user = await client.get_entity(creator.user_id)
                text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            except:
                text += f"• `{creator.user_id}`\n"
        await event.reply(text)
    except Exception as e:
        logger.error(f"Error in list_creators_logic: {e}", exc_info=True)
        await event.reply("**ماكدرت اجيب قائمة المنشئين، اكو خطأ صار 😢**")

async def clear_all_creators_logic(event, command_text):
    try:
        actor_rank = await get_user_rank(event.client, event.sender_id, event.chat_id)
        if actor_rank < Ranks.OWNER:
            return await event.reply("**بس المالك يكدر يسوي هيج شغلة خطيرة 👑**")

        async with AsyncDBSession() as session:
            await session.execute(delete(Creator).where(Creator.chat_id == event.chat_id))
            await session.commit()

        await event.reply("**🗑️ | تم مسح كل المنشئين.**")
    except Exception as e:
        logger.error(f"Error in clear_all_creators_logic: {e}", exc_info=True)
        await event.reply("**صارت مشكلة وماكدرت امسحهم 😢**")