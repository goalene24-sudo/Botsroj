import asyncio
import json
import random
from telethon import events, Button
from telethon.errors.rpcerrorlist import MessageNotModifiedError
from sqlalchemy.future import select
from sqlalchemy import func

from bot import client, StartTime
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import AsyncDBSession
from models import Chat, User, GlobalSetting

# --- استيراد الدوال المساعدة المحدثة ---
from .utils import (
    is_admin, has_bot_permission, GEMINI_ENABLED, MAIN_MENU_MESSAGE,    
    build_main_menu_buttons, build_protection_menu, get_uptime_string,
    get_or_create_user, add_points, get_global_setting,
    get_user_rank, Ranks
)
from .interactive_callbacks import handle_interactive_callback
from .services import SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM
from .menu_texts import (
    FUN_MENU_TEXT, PROFILE_MENU_TEXT, SOCIAL_MENU_TEXT, TOOLS_MENU_TEXT,
    SERVICES_MENU_TEXT, REPLIES_MENU_TEXT, SHOP_MENU_TEXT
)
from .admin import get_or_create_chat, set_chat_setting
from .games import CURRENT_QUIZZES

@client.on(events.CallbackQuery)
async def callback_handler(event):
    client = event.client
    query_data = event.data.decode('utf-8')
    chat_id = event.chat_id
    user_id = event.sender_id
    
    main_menus = [
        "fun_menu", "profile_menu", "shop_menu", "tools_menu",
        "services_menu", "replies_menu", "about_menu", "back_to_main",
        "protection_menu", "seerah_main", "hisn_main", "social_menu"
    ]

    if query_data.startswith("custom_cmd:"):
        command_name = query_data.split(':')[1]
        
        custom_commands = await get_global_setting("custom_commands", {})
        
        if command_name not in custom_commands:
            return await event.answer("⚠️ | عذراً، لم يعد هذا الأمر موجوداً.", alert=True)

        command_data = custom_commands[command_name]
        reply_template = command_data.get("reply")
        display_mode = command_data.get("display_mode", "popup")

        if not reply_template:
            return await event.answer("⚠️ | لا يوجد نص رد لهذا الأمر.", alert=True)

        async with AsyncDBSession() as session:
            sender = await event.get_sender()
            chat = await event.get_chat()
            user = await get_or_create_user(session, chat.id, sender.id)

            try:
                if not isinstance(reply_template, str):
                    reply_template = str(reply_template)
                
                final_reply = reply_template.format(
                    user_first_name=sender.first_name,
                    user_mention=f"[{sender.first_name}](tg://user?id={sender.id})",
                    user_id=sender.id,
                    points=user.points,
                    msg_count=user.msg_count,
                    chat_title=chat.title
                )

                if display_mode == "edit":
                    back_button = Button.inline("🔙 رجوع", data="back_to_main")
                    try:
                        await event.edit(final_reply, buttons=back_button, parse_mode='md', link_preview=False)
                    except MessageNotModifiedError:
                        pass
                else: # popup mode
                    popup_reply = final_reply.replace(f"[{sender.first_name}](tg://user?id={sender.id})", sender.first_name)
                    await event.answer(popup_reply, alert=True)

            except Exception as e:
                print(f"Error in custom command formatting: {e}")
                await event.answer(f"⚠️ | خطأ في عرض الرد.", alert=True)
        return

    if query_data.startswith("activate_"):
        user_rank = await get_user_rank(client, user_id, chat_id)
        if user_rank < Ranks.MOD:
            return await event.answer("🚫 | هذا الزر مخصص للمشرفين وطاقم الإدارة فقط!", alert=True)

        me = await client.get_me()
        
        if not await is_admin(client, chat_id, me.id):
            return await event.answer("🤷‍♂️ | يرجى ترقيتي لمشرف أولاً حتى أتمكن من العمل!", alert=True)

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, chat_id)

            # --- (تمت الإضافة هنا) التحقق من وجود قفل المطور ---
            if (chat.settings or {}).get('dev_lock'):
                return await event.answer("لا يمكن تفعيل البوت. تم إيقافه من قبل المطور الرئيسي.", alert=True)
            
            if chat.is_active:
                await event.answer("✅ | البوت مُفعّل أصلاً!", alert=True)
                try:
                    await event.delete()
                except:
                    pass
                return

            chat.is_active = True
            await session.commit()
            await event.edit("**✅ | تم تفعيل البوت بنجاح!**\n**أنا جاهز لتنفيذ الأوامر.**", buttons=None)
            await event.answer("💚 | تم التفعيل!")
        return

    if query_data in main_menus:
        text_to_show, buttons_to_show = None, await build_main_menu_buttons()
        if query_data == "fun_menu":
            text_to_show = FUN_MENU_TEXT
            if GEMINI_ENABLED: text_to_show += "\n\n**الذكي مال المجموعة:**\n**`اسأل + سؤالك`**"
        elif query_data == "profile_menu": text_to_show = PROFILE_MENU_TEXT
        elif query_data == "social_menu": text_to_show = SOCIAL_MENU_TEXT
        elif query_data == "tools_menu": text_to_show = TOOLS_MENU_TEXT
        elif query_data == "services_menu": text_to_show = SERVICES_MENU_TEXT
        elif query_data == "replies_menu": text_to_show = REPLIES_MENU_TEXT
        elif query_data == "shop_menu": text_to_show = SHOP_MENU_TEXT
        elif query_data == "back_to_main": text_to_show = MAIN_MENU_MESSAGE
        elif query_data == "about_menu":
            await event.answer("جاري حساب الإحصائيات...", alert=False)
            async with AsyncDBSession() as session:
                total_groups = (await session.execute(select(func.count(Chat.id)).where(Chat.is_active == True))).scalar_one()
                total_users = (await session.execute(select(func.count(func.distinct(User.user_id))))).scalar_one()
            uptime = get_uptime_string(StartTime)
            description = "أنا بوت خدمي وترفيهي وإداري،\nتم تطويري لكي البي جميع احتياجاتك."
            about_text = (f"**ℹ️ حول البوت سُـرُوچ**\n\n{description}\n\n**📈 إحصائياتي الحالية:**\n- أخدم حالياً في:** `{total_groups or 0}` **مجموعة.**\n- أتفاعل مع:** `{total_users or 0}` **مستخدم.**\n- أعمل بدون توقف منذ:** `{uptime}`\n")
            buttons = [[Button.url("👨‍💻 المطور", "https://t.me/tit_50")], [Button.inline("🔙 عودة", data="back_to_main")]]
            try: await event.edit(about_text, buttons=buttons, link_preview=False)
            except MessageNotModifiedError: pass
            return
        elif query_data == "protection_menu":
            if not await has_bot_permission(client, event): return await event.answer("**قسم الحماية بس للمشرفين.**", alert=True)
            menu_text, menu_buttons = "**🛡️ قائمة الحماية التفاعلية** 🛡️\n**دوس على أي دگمة حتى تغير حالتها.**", await build_protection_menu(event.chat_id)
            try:
                protection_msg = await event.edit(menu_text, buttons=menu_buttons)
                await set_chat_setting(event.chat_id, "protection_menu_msg_id", protection_msg.id)
            except MessageNotModifiedError: pass
            return
        elif query_data == "seerah_main":
            text = "**صلى الله على محمد ﷺ**\n\n**اختر مرحلة من السيرة النبوية:**"
            buttons = [[Button.inline(value["button"], data=f"seerah:{key}")] for key, value in SEERAH_STAGES.items()]
            buttons.append([Button.inline("🔙 عودة", data="services_menu")])
            try: await event.edit(text, buttons=buttons)
            except MessageNotModifiedError: pass
            return
        elif query_data == "hisn_main":
            text, buttons = "**حصن المسلم**\n\n**اختر الدعاء:**", [[Button.inline(value["button"], data=f"hisn:{key}")] for key, value in HISN_ALMUSLIM.items()]
            buttons.append([Button.inline("🔙 عودة", data="services_menu")])
            try: await event.edit(text, buttons=buttons)
            except MessageNotModifiedError: pass
            return
        if text_to_show:
            try: await event.edit(text_to_show, buttons=buttons_to_show)
            except MessageNotModifiedError: pass

    elif query_data.startswith("quiz:"):
        result = query_data.split(":")[1]
        msg_id = event.message_id

        if msg_id not in CURRENT_QUIZZES:
            return await event.answer("انتهى وقت هذا الكويز أو تم الإجابة عليه بالفعل.", alert=True)

        quiz_info = CURRENT_QUIZZES[msg_id]
        if user_id in quiz_info["participants"]:
            return await event.answer("لقد قمت بالمحاولة بالفعل!", alert=True)

        quiz_info["participants"].add(user_id)
        
        user_entity = await event.get_sender()
        original_message = await event.get_message()
        question_text = original_message.text.split('\n\n')[1]
        correct_answer_text = quiz_info['correct_answer']

        if result == "1":
            points_to_win = random.randint(15, 50)
            await add_points(event.chat_id, user_id, points_to_win)
            
            reply_text = (
                f"**{question_text}**\n\n"
                f"**🏆 إجابة صحيحة!**\n"
                f"**الفائز هو [{user_entity.first_name}](tg://user?id={user_id}) وقد ربح {points_to_win} نقطة!**\n"
                f"**الإجابة كانت بالفعل: {correct_answer_text}**"
            )
            await event.edit(reply_text, buttons=None)
            del CURRENT_QUIZZES[msg_id]
        else:
            await event.answer(f"للاسف إجابتك خاطئة يا {user_entity.first_name}! 😥", alert=True)
        return
        
    elif query_data.startswith("toggle_lock:"):
        if not await has_bot_permission(client, event): return await event.answer("**قسم الحماية بس للمشرفين.**", alert=True)
        lock_key = query_data.split(":")[1]
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, event.chat_id)
            if chat.lock_settings is None: chat.lock_settings = {}
            new_lock_settings = chat.lock_settings.copy()
            current_state = new_lock_settings.get(lock_key, False)
            new_lock_settings[lock_key] = not current_state
            chat.lock_settings = new_lock_settings
            await session.commit()
        new_buttons = await build_protection_menu(event.chat_id)
        try: await event.edit(buttons=new_buttons)
        except MessageNotModifiedError: pass

    elif not query_data.startswith("admin_hub:") and not query_data.startswith("settings:"):
        await handle_interactive_callback(event)
