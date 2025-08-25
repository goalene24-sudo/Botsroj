import json
from telethon import Button
import config
from bot import client
from datetime import datetime
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin, ChannelParticipantsAdmins
from telethon.errors import ChatAdminRequiredError
from telethon.errors.rpcerrorlist import UserNotParticipantError

# --- (جديد) تعريف مستويات الرتب ---
class Ranks:
    MEMBER = 0
    GROUP_ADMIN = 1
    BOT_ADMIN = 2
    CREATOR = 3
    OWNER = 4
    DEVELOPER = 5

try:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    GEMINI_ENABLED = True
    print(">> تم تفعيل الذكاء الاصطناعي Gemini بنجاح.")
except (ImportError, AttributeError):
    print(">> تحذير: مكتبة Gemini غير مثبتة أو لم يتم العثور على المفتاح. ميزات الذكاء الاصطناعي ستكون معطلة.")
    GEMINI_ENABLED = False

DB_FILE = "database.json"
RPS_GAMES = {}
XO_GAMES = {}
FLOOD_TRACKER = {}
BLESS_COUNTERS = {}

JOKES = [
    "اكو واحد راح للطبيب گاله دكتور عندي إسهال، الطبيب گاله حلّل، گال لعد شعبالك قابل مخثر؟",
    "فد يوم واحد گال لمرته: اليوم اريد اكل بره، مرته حطتله الاكل بالسطح.",
    "اكو واحد سال صاحبه گله شنو رأيك بالحب قبل الزواج؟ گله يلهي عن الزج.",
    "اكو فد واحد خبيث صعد بالباص شاف بنيه واكفه گعد بمكانها وگلها تفضلي.",
    "واحد سأل محشش: شنو الفرق بين الأسبوع والصحراء؟ گله المحشش: بسيطة، الصحراء ما بيها أحد والأسبوع بي أحد.",
    "محشش يسوق سيارة أبوه، أبوه دزله رسالة: ابني دير بالك على نفسك بالطريق. رد عليه برسالة: لا تخاف يابه آني دايسوق السيارة مو نفسي.",
    "واحد غبي اشترى موبايل جديد، خابر على نفسه وگال: هلا والله شلونك؟ شخبارك؟",
    "أستاذ يسأل طلابه: من هو الحيوان الذي يوقظكم صباحاً؟ جاوب طالب: أبويه.",
    "محشش راح يخطب، أهل العروسة سألوه: شنو تشتغل؟ گالهم: فنان. سألوه: ترسم لو تنحت؟ گالهم: لا، أفلّس.",
    "مرة واحد بخيل جاب لبيته 3 تفاحات، مرته گالتله: ليش بس تلاثة؟ گاللها: مو انتو تلاثة، تردين آكل وحدي؟",
    "محشش شاف لافتة مكتوب عليها 'مزرعة أبقار'، سأل راعي المزرعة: شلون تزرعون البقر؟ گله الراعي: نرش سكر ويطلع بقر. راح المحشش ثاني يوم رش سكر، رجع لگه النمل ملموم، گال: يا سبحان الله شوف البقر شكد حلو وهو صغير.",
    "واحد گال لصاحبه: أريد أخطب. گاله صاحبه: خوش فكرة، بس منو؟ گاله: أي وحدة، المهم أخلص من أمي.",
    "بخيل مات، لگوا بوصيته كاتب: لا تغسلوني، آني سبحت البارحة.",
    "واحد راح يشتري ساعة، سأل أبو المحل: بيش الساعة؟ گاله: كل وحدة وسعرها. گاله: لعد انطيني أم اللاش.",
    "محشش سأل صاحبه: شنو أحلى شي بالدنيا؟ گاله: النوم. گاله: زين وشنو أحلى شي بالنوم؟ گاله: من تحلم إنك نايم.",
    "مرة مدرس سأل طالب: شنو عاصمة إسبانيا؟ الطالب سكت. المدرس گاله: مدريد. الطالب گاله: والله أدري بس ما أريد أجاوب.",
    "واحد فتح محل ملابس، أول يوم محد اشترى منه. ثاني يوم هم محد اشترى. ثالث يوم قفل المحل وكتب: 'سأعود بعد قليل، ذهبت لأشتري من نفسي'.",
    "محشش ضيع مفتاح سيارته، صار يدور عليه. صاحبه گاله: وين ضيعته؟ گاله: بالسيارة. گاله صاحبه: لعد ليش تدور هنا؟ گاله: مو هنا الضوه أقوى.",
    "واحد سأل الثاني: ليش الفراعنة كانوا يبنون الأهرامات؟ گاله الثاني: لأن كانوا يخافون من الشمس.",
    "بخيل اشترى آيفون، حطه بوضع الطيران حتى لا يصرف رصيد.",
    "محشش يسأل أبوه: يابه صدك الحب أعمى؟ گاله أبوه: باوع على أمك وانت تعرف.",
    "واحد غبي راح للمطعم، طلب شوربة. الجرسون جابله الشوربة والخبز. الغبي گام يغمس الخبز بالبيبسي.",
    "محشش راح للمتحف، شاف تمثال حصان وعليه فارس. سأل الدليل: منو هذا؟ گاله الدليل: هذا صلاح الدين. گاله المحشش: زين والفرس اللي تحته منو؟",
    "واحد گال لأبوه: أريد أتزوج. أبوه گاله: منو؟ گاله: جدتي. أبوه گاله: ولك هاي أمي، تتزوج أمي؟ گاله: عادي، مو انت هم متزوج أمي؟"
]
RIDDLES = [
    ("شنو الشي اللي كلما تاخذ منه يكبر؟", "الحفرة"),
    ("شنو الشي اللي يمشي بلا رجلين ويبچي بلا عيون؟", "الغيمة"),
    ("شنو الشي اللي عنده سنون بس ما ياكل؟", "المشط"),
    ("شنو الشي اللي تشوفه بالليل تلث مرات وبالنهار مرة وحدة؟", "حرف اللام"),
    ("ما هو الشيء الذي له عين ولا يرى؟", "الإبرة"),
    ("ما هو الشيء الذي قلبه يأكل قشره؟", "الشمعة المشتعلة"),
    ("ما هو الشيء الذي يوجد في وسط باريس؟", "حرف الراء"),
    ("ما هو الشيء الذي كلما طال قصر؟", "العمر"),
    ("ما هو الشيء الذي إذا غليته تجمد؟", "البيض"),
    ("ما هو الشيء الذي له أوراق وليس بنبات، وله جلد وليس بحيوان، وعلم وليس بإنسان؟", "الكتاب"),
    ("ما هو الشيء الذي يخترق الزجاج ولا يكسره؟", "الضوء"),
    ("يسير بلا رجلين ولا يدخل إلا بالأذنين، ما هو؟", "الصوت"),
    ("ما هو الشيء الذي إذا لمسته صاح؟", "الجرس"),
    ("حامل ومحمول، نصفه ناشف ونصفه مبلول، فما هو؟", "السفينة"),
    ("تراه في الدقيقة مرتين وفي القرن مرة واحدة؟", "حرف القاف"),
    ("ما هو الشيء الذي له رقبة وليس له رأس؟", "الجاجة"),
    ("ما هو الشيء الذي ينبض بلا قلب؟", "الساعة"),
    ("ما هو الشيء الذي ترميه كلما احتجت إليه؟", "شبكة الصيد"),
    ("ما هو الشيء الذي يوصلك من بيتك إلى عملك دون أن يتحرك؟", "الطريق"),
    ("ما هو البيت الذي ليس فيه أبواب ولا نوافذ؟", "بيت الشعر"),
    ("ما هو الشيء الذي تأكل منه وهو لا يؤكل؟", "الصحن"),
    ("ما هو الشيء المليء بالثقوب ولكنه يحتفظ بالماء؟", "الإسفنج"),
    ("ما هي التي ترى كل شيء وليس لها عيون؟", "المرآة"),
    ("أخت خالك وليست خالتك، فمن تكون؟", "أمك"),
    ("ما هو الشيء الذي أمامك دائمًا ولكنك لا تراه؟", "المستقبل"),
    ("ما هو الشيء الذي يموت إذا شرب؟", "النار"),
    ("ابن أمك وأبيك وليس بأخيك ولا أختك؟", "أنت"),
    ("ما هو الشيء الذي له أربع أرجل ولا يستطيع المشي؟", "الكرسي"),
    ("ما هو الشيء الذي يكتب ولا يقرأ؟", "القلم"),
    ("ما هو الشيء الذي إذا وضعته في الثلاجة لا يبرد؟", "الفلفل الحار"),
    ("ما هو الشيء الذي له رأسين وثمانية أقدام؟", "شخصان يحملان طاولة"),
    ("شيء لونه أسود وقلبه أبيض ويرتدي قبعة على رأسه؟", "الباذنجان"),
    ("ما هو الشيء الذي يصعد الجبل بثلاثة أرجل وينزل برجل واحدة؟", "الرجل العجوز مع عكازه")
]
QUOTES = [ "اي والله صدك.", "هذا الحچي المعدل.", "مافتهمت بس مبين قافل.", "خوش حچي.", "بالضبط.", "هاي حقيقة ما ينضحك عليها.", "لهالسبب آني أحب هاي المجموعة." ]

def load_db():
    try:
        with open("database.json", 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return {}

def save_db(data):
    with open("database.json", 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

def get_uptime_string(start_time):
    uptime_delta = datetime.now() - start_time
    days = uptime_delta.days
    hours, rem = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = ""
    if days > 0: uptime_str += f"{days} يوم و "
    if hours > 0: uptime_str += f"{hours} ساعة و "
    if minutes > 0: uptime_str += f"{minutes} دقيقة"
    return uptime_str.strip().strip('و ') or "بضع ثواني"

MAIN_MENU_MESSAGE = """- - - - - - - - - - - - - - - - - -
⚜️ **قائمة أوامر سُرُوچ الرئيسية** ⚜️
- - - - - - - - - - - - - - - - - -

هلا والله! 👋 آني سُـرُوچ، مساعدك الرقمي بالمجموعة.

اختر أحد الأقسام من القائمة أدناه: 👇"""

MAIN_MENU_BUTTONS = [
    [Button.inline("م2 التفاعل 👥", data="social_menu"), Button.inline("م1 الالعاب 🎮", data="fun_menu")],
    [Button.inline("م4 المتجر 🛒", data="shop_menu"), Button.inline("م3 ملفي 👤", data="profile_menu")],
    [Button.inline("م6 الإدارة ⚙️", data="admin_hub:main"), Button.inline("م5 الادوات 🛠️", data="tools_menu")],
    [Button.inline("م8 الردود 💬", data="replies_menu"), Button.inline("م7 الدينيه 🕌", data="services_menu")],
    [Button.inline("م9 حول البوت ℹ️", data="about_menu")]
]

LOCK_TYPES = { "الصور": "photo", "الفيديو": "video", "المتحركة": "gif", "الملصقات": "sticker", "الروابط": "url", "المعرفات": "username", "التوجيه": "forward", "البوتات": "bot", "التكرار": "anti_flood" }
PERCENT_COMMANDS = [ "نسبة الحب", "نسبة الكره", "نسبة الجمال", "نسبة الغباء", "نسبة الخيانة", "نسبة الشجاعة", "نسبة الذكاء" ]
GAME_COMMANDS = ["نكتة", "حزورة", "كت", "حجره ورقه مقص", "xo", "الترتيب", "زواج", "كويز", "تخمين", "سمايلات", "سمايل", "سجلي", "المختلف", "اعلام الدول", "عواصم الدول", "رياضيات", "العكس", "اكمل المثل", "محيبس"]
ADMIN_COMMANDS = [ "القوانين", "تعديل القوانين", "ضع ترحيب", "حظر", "كتم", "الغاء الحظر", "الغاء الكتم", "رفع مشرف", "تنزيل مشرف", "رفع ادمن", "تنزيل ادمن", "الادمنيه", "تحذير", "حذف التحذيرات" ]

async def is_admin(chat_id, user_id):
    if chat_id < 0:
        try:
            participant = await client.get_permissions(chat_id, user_id)
            return participant.is_admin or participant.is_creator
        except (UserNotParticipantError, ChatAdminRequiredError): return False
        except Exception: return False
    return False

async def get_user_rank(user_id, event):
    """دالة جديدة ومحسنة لتحديد رتبة المستخدم بشكل هرمي."""
    chat_id = event.chat_id
    chat_id_str = str(chat_id)
    
    if user_id in config.SUDO_USERS:
        return Ranks.DEVELOPER
    
    try:
        async for p in client.iter_participants(chat_id, filter=ChannelParticipantsAdmins):
            if p.id == user_id and isinstance(p.participant, ChannelParticipantCreator):
                return Ranks.OWNER
    except Exception:
        pass
    
    creators = db.get(chat_id_str, {}).get("creators", [])
    if user_id in creators:
        return Ranks.CREATOR

    bot_admins = db.get(chat_id_str, {}).get("bot_admins", [])
    if user_id in bot_admins:
        return Ranks.BOT_ADMIN
    
    try:
        participant = await client.get_permissions(chat_id, user_id)
        if participant.is_admin or participant.is_creator:
            return Ranks.GROUP_ADMIN
    except (UserNotParticipantError, ChatAdminRequiredError):
        pass
    except Exception:
        pass

    return Ranks.MEMBER

async def has_bot_permission(event):
    """دالة قديمة للتحقق بشكل عام إذا كان المستخدم مشرفاً أو أعلى."""
    rank = await get_user_rank(event.sender_id, event)
    return rank >= Ranks.GROUP_ADMIN

async def check_activation(chat_id):
    """دالة للتحقق إذا كان البوت مفعلاً في المجموعة."""
    chat_id_str = str(chat_id)
    is_paused = db.get(chat_id_str, {}).get("is_paused", False)
    if is_paused:
        return False
    return True

def add_points(chat_id, user_id, points_to_add):
    chat_id_str, user_id_str = str(chat_id), str(user_id)
    if chat_id_str not in db: db[chat_id_str] = {}
    if "users" not in db[chat_id_str]: db[chat_id_str]["users"] = {}
    if user_id_str not in db[chat_id_str]["users"]: db[chat_id_str]["users"][user_id_str] = {"msg_count": 0, "sahaqat": 0, "points": 0}
    if "points" not in db[chat_id_str]["users"][user_id_str]: db[chat_id_str]["users"][user_id_str]["points"] = 0
    db[chat_id_str]["users"][user_id_str]["points"] += points_to_add; save_db(db)

async def build_protection_menu(chat_id):
    chat_id_str, chat_locks = str(chat_id), db.get(str(chat_id), {})
    buttons, row = [], []
    for name, key in LOCK_TYPES.items():
        status_emoji = "🔒" if chat_locks.get(key, False) else "🔓"
        button = Button.inline(f"{status_emoji} {name}", data=f"toggle_lock_{key}")
        row.append(button)
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    # تم تغيير هذا الزر ليعود إلى قائمة الإدارة الجديدة بدلاً من القائمة الرئيسية
    buttons.append([Button.inline("🔙 رجوع", data="admin_hub:main")])
    return buttons

def build_xo_keyboard(board):
    buttons = []
    for i in range(0, 9, 3):
        row = [Button.inline(board[j] if board[j] != '-' else ' ', data=f"xo_move_{j}") for j in range(i, i + 3)]
        buttons.append(row)
    return buttons

def check_xo_winner(board):
    lines = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4
,6)]
    for line in lines:
        if board[line[0]] == board[line[1]] == board[line[2]] != '-':
            return board[line[0]]
    if '-' not in board: return 'draw'
    return None
