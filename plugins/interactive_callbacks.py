import time
import random
from telethon import events, Button
from telethon.errors.rpcerrorlist import MessageNotModifiedError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.future import select
from sqlalchemy import delete
import config # <-- تم إضافة هذا

from bot import client
# --- استيراد مكونات قاعدة البيانات من المصدر الصحيح ---
from database import AsyncDBSession
from models import RPSGame, Whisper
# --- استيراد الدوال المساعدة المحدثة ---
from .utils import (
    check_activation, RPS_GAMES, XO_GAMES,
    build_protection_menu, build_xo_keyboard,
    check_xo_winner, add_points, has_bot_permission,
    RIDDLES, BLESS_COUNTERS, is_admin,
    get_user_rank, Ranks
)
from .utils import get_or_create_chat, get_or_create_user
from .fun import WYR_GAMES, PROPOSALS, DICE_GAMES
from .games import MAHIBES_GAMES
from .services import SEERAH_STAGES
from .hisn_almuslim_data import HISN_ALMUSLIM

TASBEEH_COOLDOWN = {}
TASBEEH_CLICK_COOLDOWN = 1

async def handle_interactive_callback(event):
    client = event.client
    user_id, chat_id, query_data = event.sender_id, event.chat_id, event.data.decode('utf-8')
    data_parts = query_data.split(':')
    action = data_parts[0]

    if query_data.startswith("activate_"):
        user_rank = await get_user_rank(client, user_id, chat_id)
        if user_rank < Ranks.MOD:
            return await event.answer("🚫 | هذا الزر مخصص للمشرفين وطاقم الإدارة فقط!", alert=True)

        me = await client.get_me()
        
        if not await is_admin(client, chat_id, me.id):
            return await event.answer("🤷‍♂️ | يرجى ترقيتي لمشرف أولاً حتى أتمكن من العمل!", alert=True)

        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, chat_id)
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

    if query_data.startswith("toggle_lock_"):
        if not await has_bot_permission(client, event):
            return await event.answer("**قسم الحماية بس للمشرفين والأدمنية.**", alert=True)
        
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, chat_id)
            lock_settings = chat.lock_settings or {}
            
            lock_key = query_data.replace("toggle_lock_", "")
            
            current_state = lock_settings.get(lock_key, False)
            lock_settings[lock_key] = not current_state
            
            chat.lock_settings = lock_settings
            flag_modified(chat, "lock_settings")
            await session.commit()
            
            action_text = "قفل" if lock_settings[lock_key] else "فتح"
            await event.answer(f"تم {action_text} بنجاح.")
            await event.edit(buttons=await build_protection_menu(chat_id))
        return

    if action == "rps":
        msg_id = event.message_id
        
        async with AsyncDBSession() as session:
            result = await session.execute(select(RPSGame).where(RPSGame.message_id == msg_id))
            game = result.scalar_one_or_none()

            if not game:
                return await event.answer("🚫 | **هذا التحدي قديم أو انتهى.**", alert=True)

            p1_id, p2_id = game.player1_id, game.player2_id
            
            p1_id_from_data = int(data_parts[2])
            p2_id_from_data = int(data_parts[3])

            if user_id not in [p1_id_from_data, p2_id_from_data]:
                return await event.answer("🤨 | **هذا التحدي مو إلك!**", alert=True)
            
            player_choice = data_parts[1]
            
            if user_id == p1_id:
                if game.player1_choice:
                    return await event.answer("✅ | **انتظر خصمك، انت اخترت خلاص.**", alert=True)
                game.player1_choice = player_choice
            else: # user_id == p2_id
                if game.player2_choice:
                    return await event.answer("✅ | **انتظر خصمك، انت اخترت خلاص.**", alert=True)
                game.player2_choice = player_choice
            
            if game.player1_choice and game.player2_choice:
                p1_name, p2_name = game.player1_name, game.player2_name
                p1_c, p2_c = game.player1_choice, game.player2_choice
                
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
                
                await session.execute(delete(RPSGame).where(RPSGame.message_id == msg_id))

            else:
                await event.answer("✅ | **تم تسجيل اختيارك! ننتظر اللاعب الثاني...**", alert=True)
            
            await session.commit()
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

    if action == "whisper":
        sub_action = data_parts[1]
        msg_id = event.message_id
        if sub_action == "read":
            # --- سطر تشخيصي مضاف ---
            if user_id in config.SUDO_USERS:
                await client.send_message(user_id, "**DEBUG (READ):**\n**تم استدعاء معالج القراءة. جاري البحث في قاعدة البيانات...**")

            async with AsyncDBSession() as session:
                result = await session.execute(select(Whisper).where(Whisper.message_id == msg_id))
                whisper_data = result.scalar_one_or_none()

                if not whisper_data:
                    if user_id in config.SUDO_USERS:
                         await client.send_message(user_id, "**DEBUG (READ):**\n**لم يتم العثور على الهمسة في قاعدة البيانات (whisper_data is None).**")
                    return await event.answer("**عذراً، هذه الهمسة قديمة جداً أو تم حذفها.**", alert=True)
                
                # --- سطر تشخيصي مضاف ---
                if user_id in config.SUDO_USERS:
                    await client.send_message(user_id, f"**DEBUG (READ):**\n**تم العثور على الهمسة.**\n**النص المسترجع:** `{whisper_data.text}`")

                if user_id == whisper_data.to_id:
                    whisper_text = whisper_data.text
                    await event.answer(f"**🤫 الهمسة تقول:\n\n{whisper_text}**", alert=True)
                    await event.edit(buttons=Button.inline("✅ تم قراءة الهمسة", data="whisper:done"))
                    
                    await session.delete(whisper_data)
                    await session.commit()
                else:
                    await event.answer("🚫 | **هذه الهمسة ليست لك!**", alert=True)
        
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
        
    if action == "show_rules":
        user = await event.get_sender()
        async with AsyncDBSession() as session:
            chat = await get_or_create_chat(session, chat_id)
            rules = (chat.settings or {}).get("rules")
        
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
