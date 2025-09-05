# plugins/interactive_callbacks.py
import time
import random
from datetime import datetime, timedelta
from telethon import events, Button
from bot import client
import config
from .utils import (
    db, save_db, is_admin, check_activation, RPS_GAMES, XO_GAMES,
    build_protection_menu, build_xo_keyboard, 
    check_xo_winner, add_points, has_bot_permission,
    RIDDLES, BLESS_COUNTERS, build_main_menu_buttons
)
# --- تم تغيير المسار إلى social.py ---
from .social import WYR_GAMES, WHISPERS, PROPOSALS, DICE_GAMES
from .games import CURRENT_QUIZZES, MAHIBES_GAMES
from .services import TASBEEH_AZKAR, NAMES_OF_ALLAH, SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM

TASBEEH_COOLDOWN = {}
TASBEEH_CLICK_COOLDOWN = 3

async def handle_interactive_callback(event):
    user_id, chat_id, query_data = event.sender_id, event.chat_id, event.data.decode('utf-8')
    data_parts = query_data.split(':')
    action = data_parts[0]
    chat_id_str = str(chat_id)

    if query_data.startswith("toggle_lock_"):
        if not await has_bot_permission(event): 
            return await event.answer("**قسم الحماية بس للمشرفين والأدمنية.**", alert=True)
        
        if chat_id_str not in db: db[chat_id_str] = {}
        
        db_key = query_data.replace("toggle_", "") 
        
        current_state = db[chat_id_str].get(db_key, False)
        db[chat_id_str][db_key] = not current_state
        save_db(db)
        
        action_text = "قفل" if db[chat_id_str][db_key] else "فتح"
        await event.answer(f"تم {action_text} بنجاح.")

        await event.edit(buttons=await build_protection_menu(chat_id))
        return

    if action == "mahbis":
        game = MAHIBES_GAMES.get(chat_id)
        if not game:
            return await event.answer("هاي اللعبة خلصانة.", alert=True)

        player_id = game["player_id"]
        if user_id != player_id:
            return await event.answer("هاي اللعبة مو الك! اذا تريد تلعب، اكتب `محيبس`", alert=True)

        guess_pos = int(data_parts[2])
        winner_pos = game["winner_pos"]

        if guess_pos == winner_pos:
            winner = await event.get_sender()
            add_points(chat_id, winner.id, 50)
            
            buttons = [Button.inline("💍" if i == winner_pos else "✊", data="mahbis:done") for i in range(5)]
            keyboard = [buttons]
            
            await event.edit(f"**كفوووو! [{winner.first_name}](tg://user?id={winner.id}) لزمت المحيبس! 💎 ربحت 50 نقطة.**", buttons=keyboard)
            del MAHIBES_GAMES[chat_id]
        else:
            await event.answer("ايدك فارغة! حاول مرة لخ.", alert=True)
        return

    if action == "proposal":
        sub_action, proposer_id, proposed_id = data_parts[1], int(data_parts[2]), int(data_parts[3])
        msg_id = event.message_id
        if user_id != proposed_id:
            return await event.answer("**هذا الطلب موجه لشخص آخر.**", alert=True)
        proposal_data = PROPOSALS.get(msg_id)
        if not proposal_data:
            return await event.answer("**هذا الطلب قديم أو انتهت صلاحيته.**", alert=True)
        proposer_name = proposal_data["proposer_name"]
        proposed_name = proposal_data["proposed_name"]
        if sub_action == "accept":
            text = f"**🎉 تمت الموافقة!** 🎉\n\n**مبروك للخطيبين [{proposer_name}](tg://user?id={proposer_id}) و [{proposed_name}](tg://user?id={proposed_id})! عقبال الفرحة الكبرى.**"
            await event.edit(text, buttons=None)
            proposer_id_str, proposed_id_str = str(proposer_id), str(proposed_id)
            if "users" not in db[chat_id_str]: db[chat_id_str]["users"] = {}
            if proposer_id_str not in db[chat_id_str]["users"]: db[chat_id_str]["users"][proposer_id_str] = {}
            if proposed_id_str not in db[chat_id_str]["users"]: db[chat_id_str]["users"][proposed_id_str] = {}
            db[chat_id_str]["users"][proposer_id_str]["married_to"] = {"id": proposed_id, "name": proposed_name}
            db[chat_id_str]["users"][proposed_id_str]["married_to"] = {"id": proposer_id, "name": proposer_name}
            save_db(db)
        elif sub_action == "reject":
            text = f"**💔 تم الرفض!** 💔\n\n**للأسف، [{proposed_name}](tg://user?id={proposed_id}) قام برفض طلب [{proposer_name}](tg://user?id={proposer_id}). خيرها بغيرها.**"
            await event.edit(text, buttons=None)
        del PROPOSALS[msg_id]
        return

    if action == "whisper":
        sub_action = data_parts[1]
        msg_id = event.message_id
        if sub_action == "read":
            whisper_data = WHISPERS.get(msg_id)
            if not whisper_data:
                return await event.answer("**عذراً، هذه الهمسة قديمة جداً أو تم حذفها.**", alert=True)
            recipient_id = whisper_data["to_id"]
            if user_id == recipient_id:
                whisper_text = whisper_data["text"]
                await event.answer(f"**🤫 الهمسة تقول:\n\n{whisper_text}**", alert=True)
                await event.edit(buttons=Button.inline("✅ تم قراءة الهمسة", data="whisper:done"))
                del WHISPERS[msg_id]
            else:
                await event.answer("**🚫 | هذه الهمسة ليست لك!**", alert=True)
        elif sub_action == "done":
            await event.answer("**تمت قراءة هذه الهمسة بالفعل.**", alert=True)
        return

    if action == "hisn":
        key = data_parts[1]
        dua_info = HISN_ALMUSLIM.get(key)
        if dua_info:
            text = dua_info["text"]
            buttons = Button.inline("📜 رجوع إلى القائمة", data="hisn_main")
            await event.edit(text, buttons=buttons)
        await event.answer()
        return

    if action == "seerah":
        stage_key = data_parts[1]
        stage_info = SEERAH_STAGES.get(stage_key)
        if stage_info:
            text = stage_info["text"]
            buttons = Button.inline("🔙 رجوع إلى القائمة", data="seerah_main")
            await event.edit(f"**{text}**", buttons=buttons)
        await event.answer()
        return

    if action == "asma_husna":
        sub_action = data_parts[1]
        if sub_action == "random":
            random_name = random.choice(NAMES_OF_ALLAH)
            text = f"**✨ {random_name['name']} ✨**\n\n**المعنى:**\n**{random_name['meaning']}**"
            buttons = [[Button.inline("💎 اسم آخر", data="asma_husna:random")], [Button.inline("📋 عرض القائمة كاملة", data="asma_husna:full_list")]]
            await event.edit(text, buttons=buttons)
        elif sub_action == "full_list":
            full_list_text = "**✨ أسماء الله الحسنى ✨**\n\n"
            for i, name_data in enumerate(NAMES_OF_ALLAH, 1):
                full_list_text += f"**{i}. {name_data['name']}**\n"
            await event.edit(full_list_text, buttons=Button.inline("💎 عرض اسم عشوائي مع الشرح", data="asma_husna:random"))
        await event.answer()
        return

if action == "show_rules":
        user = await event.get_sender()
        rules = db.get(chat_id_str, {}).get("rules")
        if rules:
            await event.reply(f"**اهلاً بك [{user.first_name}](tg://user?id={user.id})! تفضل قوانين المجموعة:**\n\n**{rules}**")
            await event.answer()
        else:
            await event.answer("**عذراً، لم يقم المشرفون بوضع قوانين للمجموعة بعد.**", alert=True)
    
    if action == "riddle":
        riddle_index = int(data_parts[1])
        _, riddle_a = RIDDLES[riddle_index]
        await event.edit(f"**الجواب هو: {riddle_a}**")
    
    if action == "quiz":
        user_answer, correct_answer = data_parts[1], data_parts[2]
        winner = await event.get_sender()
        if user_answer == correct_answer:
            await event.edit(f"**عفيههه عليك يا بطل [{winner.first_name}](tg://user?id={winner.id})! 👏 جوابك صح.**")
            add_points(chat_id, winner.id, 5)
        else:
            await event.edit(f"**اويليي، غلط جوابك يا [{winner.first_name}](tg://user?id={winner.id})! 😢 الجواب الصح هو '{correct_answer}'.**")
        await event.answer()

    if query_data.startswith("activate_"):
        chat_id_to_activate = int(query_data.split("_")[1])
        if not await is_admin(chat_id_to_activate, user_id): return await event.answer("**هذا الزر مخصص للمشرفين فقط.**", alert=True)
        me = await client.get_me()
        if not await is_admin(chat_id_to_activate, me.id): return await event.answer("**الرجاء رفعي مشرفاً أولاً.**", alert=True)
        if chat_id_str not in db: db[chat_id_str] = {}
        db[chat_id_str]["is_paused"] = False; save_db(db)
        buttons = build_main_menu_buttons()
        await event.edit("**✅ تم تفعيل البوت بنجاح!**\n**الآن يمكنك استخدام القوائم أدناه للتحكم.**", buttons=buttons)
    
    if query_data.startswith("rps"):
        msg_id = event.message_id
        if msg_id not in RPS_GAMES:
            return await event.edit("**هذا التحدي قديم، ابدأ تحديًا جديدًا.**", buttons=None)

        game = RPS_GAMES[msg_id]
        action_rps, choice, p1_id, p2_id = data_parts

        if user_id not in [int(p1_id), int(p2_id)]:
            return await event.answer("هذا التحدي ليس لك!", alert=True)

        if user_id == int(p1_id) and not game["p1_choice"]:
            game["p1_choice"] = choice
            await event.answer(f"اخترت {choice}. ننتظر اللاعب الثاني...")
        elif user_id == int(p2_id) and not game["p2_choice"]:
            game["p2_choice"] = choice
            await event.answer(f"اخترت {choice}. ننتظر اللاعب الثاني...")
        else:
            return await event.answer("لقد قمت بالاختيار بالفعل!", alert=True)

        if game["p1_choice"] and game["p2_choice"]:
            p1_c, p2_c = game["p1_choice"], game["p2_choice"]
            p1_n, p2_n = game["p1_name"], game["p2_name"]
            winner = None
            if p1_c == p2_c:
                result_text = "تعادل!"
            elif (p1_c == "rock" and p2_c == "scissors") or \
                 (p1_c == "paper" and p2_c == "rock") or \
                 (p1_c == "scissors" and p2_c == "paper"):
                winner = p1_n
            else:
                winner = p2_n
            
            result_message = f"**انتهى التحدي!**\n\n" \
                             f"**- {p1_n} اختار:** `{p1_c}`\n" \
                             f"**- {p2_n} اختار:** `{p2_c}`\n\n"
            if winner:
                result_message += f"**الفائز هو {winner}! 🥳**"
            else:
                result_message += f"**النتيجة تعادل! 🤝**"

            await event.edit(result_message, buttons=None)
            del RPS_GAMES[msg_id]
        return

    if query_data.startswith("xo_move_"):
        msg_id = event.message_id
        if msg_id not in XO_GAMES:
            return await event.edit("**هذه اللعبة قديمة، ابدأ لعبة جديدة.**", buttons=None)
        
        game = XO_GAMES[msg_id]
        pos = int(data_parts[1])

        if user_id != game['turn']:
            return await event.answer("مو سرآك!", alert=True)
        if game['board'][pos] != '-':
            return await event.answer("هذا المربع محجوز!", alert=True)

        game['board'][pos] = game['symbol']
        winner = check_xo_winner(game['board'])

        if winner:
            winner_name = game['p1_name'] if winner == 'X' else game['p2_name']
            result_text = f"**انتهت اللعبة! الفائز هو {winner_name} ({winner})! 🏆**"
            if winner == "draw":
                result_text = "**انتهت اللعبة بالتعادل! 🤝**"
            await event.edit(result_text, buttons=build_xo_keyboard(game['board']))
            del XO_GAMES[msg_id]
        else:
            game['turn'] = game['player_o'] if game['turn'] == game['player_x'] else game['player_x']
            game['symbol'] = 'O' if game['symbol'] == 'X' else 'X'
            turn_name = game['p1_name'] if game['turn'] == game['player_x'] else game['p2_name']
            text = f"**⚔️ لعبة XO!**\n\n**- اللاعب 𝚇:** {game['p1_name']}\n**- اللاعب 𝙾:** {game['p2_name']}\n\n**سره {turn_name} ({game['symbol']})**"
            await event.edit(text, buttons=build_xo_keyboard(game['board']))
        return
    
    if query_data.startswith("bless"):
        msg_id = event.message_id
        if msg_id not in BLESS_COUNTERS:
            return await event.answer("هذا الزواج قديم!", alert=True)
        
        counter = BLESS_COUNTERS[msg_id]
        if user_id in counter["users"]:
            return await event.answer("لقد باركت بالفعل!", alert=True)
        
        counter["users"].add(user_id)
        counter["count"] += 1
        
        chat_id_bless, event_id_bless = data_parts[1], data_parts[2]
        new_button = Button.inline(f'مباركين 🎉 ({counter["count"]})', data=f"bless:{chat_id_bless}:{event_id_bless}")
        await event.edit(buttons=new_button)
        await event.answer("💖")
        return

    if query_data.startswith("mute_"):
        try:
            _, user_to_mute_id, minutes = query_data.split("_")
            user_to_mute_id, minutes = int(user_to_mute_id), int(minutes)
            
            if not await has_bot_permission(event):
                return await event.answer("أنت لست مشرفاً!", alert=True)

            until_date = datetime.now() + timedelta(minutes=minutes)
            await client.edit_permissions(chat_id, user_to_mute_id, send_messages=False, until_date=until_date)
            
            user_to_mute = await client.get_entity(user_to_mute_id)
            await event.edit(f"**✅ تم كتم [{user_to_mute.first_name}](tg://user?id={user_to_mute_id}) لمدة {minutes} دقيقة.**")
        except Exception as e:
            await event.edit(f"**حدث خطأ:**\n`{e}`")
        return

# --- معالج جديد ومطور لضغطات أزرار الأوامر المخصصة ---
@client.on(events.CallbackQuery(pattern=b"^ccmd:(.+)"))
async def custom_command_button_handler(event):
    command_name = event.data.decode().split(':')[1]
    custom_commands = db.get("custom_commands", {})
    
    if command_name not in custom_commands:
        return await event.answer("⚠️ | عذراً، لم يعد هذا الأمر موجوداً.", alert=True)

    command_data = custom_commands[command_name]
    reply_template = command_data.get("reply")
    display_mode = command_data.get("display_mode", "popup") 

    if not reply_template:
        return await event.answer("⚠️ | لا يوجد نص رد لهذا الأمر.", alert=True)

    sender = await event.get_sender()
    chat = await event.get_chat()
    chat_id_str = str(chat.id)
    sender_id_str = str(sender.id)
    user_data = db.get(chat_id_str, {}).get("users", {}).get(sender_id_str, {})
    msg_count = user_data.get("msg_count", 0)
    points = user_data.get("points", 0)

    try:
        if not isinstance(reply_template, str):
            reply_template = str(reply_template)

        final_reply = reply_template.format(
            user_first_name=sender.first_name,
            user_mention=f"[{sender.first_name}](tg://user?id={sender.id})",
            user_id=sender.id,
            points=points,
            msg_count=msg_count,
            chat_title=chat.title
        )

        if display_mode == "edit":
            back_button = Button.inline("🔙 رجوع", data="back_to_main")
            await event.edit(final_reply, buttons=back_button, parse_mode='md')
        else:
            popup_reply = final_reply.replace(f"[{sender.first_name}](tg://user?id={sender.id})", sender.first_name)
            await event.answer(popup_reply, alert=True)

    except Exception as e:
        await event.answer(f"⚠️ | خطأ في عرض الرد: {e}", alert=True)
