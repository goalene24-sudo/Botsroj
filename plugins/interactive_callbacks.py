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
from .fun import WYR_GAMES, WHISPERS, PROPOSALS, DICE_GAMES
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
        db[chat_id_str]
