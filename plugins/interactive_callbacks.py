import time
import random
from telethon import events, Button
from telethon.errors.rpcerrorlist import MessageNotModifiedError
from sqlalchemy.orm.attributes import flag_modified

from bot import client
# --- استيراد مكونات قاعدة البيانات الجديدة ---
from database import DBSession
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import (
    check_activation, RPS_GAMES, XO_GAMES,
    build_protection_menu, build_xo_keyboard,
    check_xo_winner, add_points, has_bot_permission,
    RIDDLES, BLESS_COUNTERS
)
from .admin import get_or_create_chat, get_or_create_user
from .fun import WYR_GAMES, WHISPERS, PROPOSALS, DICE_GAMES
from .games import MAHIBES_GAMES
from .services import SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM

TASBEEH_COOLDOWN = {}
TASBEEH_CLICK_COOLDOWN = 1

async def handle_interactive_callback(event):
    user_id, chat_id, query_data = event.sender_id, event.chat_id, event.data.decode('utf-8')
    data_parts = query_data.split(':')
    action = data_parts[0]

    if query_data.startswith("toggle_lock_"):
        if not await has_bot_permission(event):
            return await event.answer("**قسم الحماية بس للمشرفين والأدمنية.**", alert=True)
        
        async with DBSession() as session:
            chat = await get_or_create_chat(session, chat_id)
            lock_settings = chat.lock_settings or {}
            
            lock_key = query_data.replace("toggle_lock_", "")
            
            current_state = lock_settings.get(lock_key, False)
            lock_settings[lock_key] = not current_state
            
            chat.lock_settings = lock_settings
            flag_modified(chat, "lock_settings") # مهم جداً لحقول JSON
            await session.commit()
            
            action_text = "قفل" if lock_settings[lock_key] else "فتح"
            await event.answer(f"تم {action_text} بنجاح.")
            await event.edit(buttons=await build_protection_menu(chat_id))
        return

    if action == "rps":
        msg_id = event.message_id
        game = RPS_GAMES.get(msg_id)
        if not game:
            return await event.answer("🚫 | **هذا التحدي قديم أو انتهى.**", alert=True)

        player_choice, p1_id, p2_id = data_parts[1], int(game["p1"]), int(game["p2"])

        if user_id not in [p1_id, p2_id]:
            return await event.answer("🤨 | **هذا التحدي مو إلك!**", alert=True)
        
        player_key = "p1_choice" if user_id == p1_id else "p2_choice"
        if game[player_key]:
            return await event.answer("✅ | **انتظر خصمك، انت اخترت خلاص.**", alert=True)

        game[player_key] = player_choice
        
        if game["p1_choice"] and game["p2_choice"]:
            p1_name, p2_name = game["p1_name"], game["p2_name"]
            p1_c, p2_c = game["p1_choice"], game["p2_choice"]
            
            choice_emojis = {"rock": "🗿", "paper": "📄", "scissors": "✂️"}
            p1_e, p2_e = choice_emojis[p1_c], choice_emojis[p2_c]

            win_conditions = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
            
            if p1_c == p2_c:
                winner_text = "**تعادل! ماكو فايز.**"
            elif (p1_c, p2_c) in win_conditions:
                winner_text = f"**الف مبروك! [{p1_name}](tg://user?id={p1_id}) فاز.**"
                await add_points(chat_id, p1_id, 25)
            else:
                winner_text = f"**الف مبروك! [{p2_name}](tg://user?id={p2_id}) فاز.**"
                await add_points(chat_id, p2_id, 25)

            result_text = f"**انتهى التحدي!**\n\n- **{p1_name} اختار:** {p1_e}\n- **{p2_name} اختار:** {p2_e}\n\n**النتيجة:** {winner_text}"
            await event.edit(result_text, buttons=None)
            del RPS_GAMES[msg_id]
        else:
            await event.answer("✅ | **تم تسجيل اختيارك! ننتظر اللاعب الثاني...**", alert=True)
        return

    if action == "xo":
        msg_id = event.message_id
        game = XO_GAMES.get(msg_id)
        if not game:
            return await event.answer("🚫 | **هذه اللعبة قديمة أو انتهت.**", alert=True)
        
        if data_parts[1] == "done":
            return await event.answer("اللعبة منتهية!", alert=True)

        if user_id != game['turn']:
            return await event.answer("😒 | **مو سرآك هسه!**", alert=True)

        pos = int(data_parts[1])
        if game['board'][pos] != '-':
            return await event.answer("❌ | **هذا المكان محجوز! اختر مكان فارغ.**", alert=True)

        game['board'][pos] = game['symbol']
        winner = check_xo_winner(game['board'])

        if winner in ['X', 'O']:
            winner_user_id = game['player_x'] if winner == 'X' else game['player_o']
            winner_name = game['p1_name'] if winner == 'X' else game['p2_name']
            await add_points(chat_id, winner_user_id, 50)
            text = f"**🎉 الف مبروك!**\n\n**الفائز هو [{winner_name}](tg://user?id={winner_user_id}) ({winner})! 🏆**\n**لقد ربحت 50 نقطة.**"
            await event.edit(text, buttons=build_xo_keyboard(game['board'], game_over=True))
            if msg_id in XO_GAMES: del XO_GAMES[msg_id]
        
        elif winner == 'draw':
            text = "**انتهت اللعبة بالتعادل! 🤝**"
            await event.edit(text, buttons=build_xo_keyboard(game['board'], game_over=True))
            if msg_id in XO_GAMES: del XO_GAMES[msg_id]
        
        else: # Game continues
            game['turn'] = game['player_o'] if game['turn'] == game['player_x'] else game['player_x']
            game['symbol'] = 'O' if game['symbol'] == 'X' else 'X'
            turn_name = game['p2_name'] if game['turn'] == game['player_o'] else game['p1_name']
            text = (f"**⚔️ لعبة XO مستمرة!**\n\n"
                    f"**- اللاعب 𝚇:** [{game['p1_name']}](tg://user?id={game['player_x']})\n"
                    f"**- اللاعب 𝙾:** [{game['p2_name']}](tg://user?id={game['player_o']})\n\n"
                    f"**سره {turn_name} ({game['symbol']})**")
            await event.edit(text, buttons=build_xo_keyboard(game['board']))
        return

    if action == "tasbeeh":
        sub_action = data_parts[1]
        zikr = data_parts[2]
        goal = int(data_parts[3])
        current = int(data_parts[4])
        
        if sub_action == "click":
            now = time.time()
            last_click = TASBEEH_COOLDOWN.get(user_id, 0)
            if now - last_click < TASBEEH_CLICK_COOLDOWN:
                return await event.answer("على كيفك، لا تضغط بسرعة!", alert=True)
            
            TASBEEH_COOLDOWN[user_id] = now
            current += 1
            
            new_data = f"tasbeeh:click:{zikr}:{goal}:{current}"
            reset_data = f"tasbeeh:reset:{zikr}:{goal}:0"
            new_buttons = [[Button.inline(f"{zikr} [{current}]", data=new_data), 
                            Button.inline("🔄 إعادة التصفير", data=reset_data)]]
            try:
                await event.edit(buttons=new_buttons)
            except MessageNotModifiedError:
                pass 

            if current == goal:
                await event.answer("تقبل الله طاعتك 🤲", alert=True)

        elif sub_action == "reset":
            current = 0
            new_data = f"tasbeeh:click:{zikr}:{goal}:0"
            reset_data = f"tasbeeh:reset:{zikr}:{goal}:0"
            new_buttons = [[Button.inline(f"{zikr} [0]", data=new_data), 
                            Button.inline("🔄 إعادة التصفير", data=reset_data)]]
            await event.edit(buttons=new_buttons)
            await event.answer("تم تصفير العداد.")
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
            await add_points(chat_id, winner.id, 50)
            
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
            
            async with DBSession() as session:
                proposer_obj = await get_or_create_user(session, chat_id, proposer_id)
                proposed_obj = await get_or_create_user(session, chat_id, proposed_id)

                proposer_inventory = proposer_obj.inventory or {}
                proposed_inventory = proposed_obj.inventory or {}

                proposer_inventory["married_to"] = {"id": proposed_id, "name": proposed_name}
                proposed_inventory["married_to"] = {"id": proposer_id, "name": proposer_name}

                proposer_obj.inventory = proposer_inventory
                proposed_obj.inventory = proposed_inventory
                
                flag_modified(proposer_obj, "inventory")
                flag_modified(proposed_obj, "inventory")
                
                await session.commit()

        elif sub_action == "reject":
            text = f"**💔 تم الرفض!** 💔\n\n**للأسف، [{proposed_name}](tg://user?id={proposed_id}) قام برفض طلب [{proposer_name}](tg://user?id={proposer_id}). خيرها بغيرها.**"
            await event.edit(text, buttons=None)
        
        if msg_id in PROPOSALS: del PROPOSALS[msg_id]
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
        # ... الكود الخاص بأسماء الله الحسنى ...
        return
        
    if action == "show_rules":
        user = await event.get_sender()
        async with DBSession() as session:
            chat = await get_or_create_chat(session, chat_id)
            rules = chat.settings.get("rules")
        
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
            await add_points(chat_id, winner.id, 5)
        else:
            await event.edit(f"**اويليي، غلط جوابك يا [{winner.first_name}](tg://user?id={winner.id})! 😢 الجواب الصح هو '{correct_answer}'.**")
        await event.answer()

