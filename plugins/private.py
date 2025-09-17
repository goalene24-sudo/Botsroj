# plugins/private.py
from telethon import events, Button
from bot import client
import config
from .utils import GEMINI_ENABLED

async def get_main_private_menu():
    me = await client.get_me()
    start_text = (
        f"**هلا والله بيك! 👋 آني البوت {me.first_name}، مساعدك الشخصي الخارق.**\n\n"
        f"**أگدر أديرلك كروب حتى لو بي 200 ألف عضو! 🦾**\n"
        f"**ضيفني لمجموعتك وتمتع بالقوة والحراسة والتفاعل طويلة المدى.**\n\n"
        f"**دوس الأزرار الجوه حتى تعرف شگدر أسوي! 👇**"
    )
    buttons = [
        [Button.url("➕ أضفني لمجموعتك ➕", f"https://t.me/{me.username}?startgroup=true")],
        [Button.inline("🎮 التسلية والألعاب 🕹️", data="private:fun_menu")],
        [
            Button.inline("👤 ملفي الشخصي", data="private:profile_menu"),
            Button.inline("🛒 المتجر", data="private:shop_menu")
        ],
        [
            Button.inline("🛡️ الحماية", data="private:protection_menu"),
            Button.inline("🛠️ أدوات المجموعة", data="private:tools_menu")
        ],
        [
            Button.inline("🕌 الخدمات الدينية", data="private:services_menu"),
            Button.inline("💬 الردود", data="private:replies_menu")
        ]
    ]
    return start_text, buttons

@client.on(events.NewMessage(
    pattern=r"(?i)^(/start|الاوامر|بوت|هلو|السلام عليكم|مرحبا)$",
    func=lambda e: e.is_private
))
async def private_message_handler(event):
    start_text, buttons = await get_main_private_menu()
    await event.reply(start_text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"^private:"))
async def private_callback_handler(event):
    action = event.data.decode('utf-8').split(":")[1]
    back_button = Button.inline("🔙 عودة", data="private:back_to_main")

    if action == "fun_menu":
        fun_text = """**🎮 قسم التسلية والألعاب 🎮**

**هذا القسم يحتوي على مجموعة واسعة من الألعاب والأوامر التفاعلية لزيادة المرح في مجموعتك، مثل:**
- **`سمايلات`**: **لعبة سرعة لإرسال السمايل المطلوب.**
- **`تحدي نرد`**: **(بالرد) لتحدي عضو في لعبة نرد.**
- **`من هو`**: **لعبة عشوائية لاختيار عضو من المجموعة.**
- **`همس [نص]`**: **(بالرد) لإرسال رسالة سرية لعضو معين.**
- **`تزوجني`** و **`طلاق`**: **نظام زواج تفاعلي.**
- **`صفعة`،`بوسة`،`عناق`**: **(بالرد) أفعال تفاعلية للمزاح.**
- **`صندوق الحظ`، `نقاطي`، `الترتيب`.**
- **ألعاب كلاسيكية مثل `xo` و `كويز` و `تخمين`.**
**وغيرها الكثير...**"""
        await event.edit(fun_text, buttons=back_button)

    elif action == "profile_menu":
        profile_text = """**👤 قسم ملفي الشخصي** 👤

**هذا القسم مخصص لكل ما يتعلق بك في المجموعة:**
- **`راتب`**: **مكافأة يومية من النقاط.**
- **`ضع نبذة`**: **لوضع نبذة تعريفية خاصة بك.**
- **`ايدي`**: **لعرض ملفك الشخصي المفصل.**
- **`اهداء`**: **لإهداء جزء من نقاطك لعضو آخر.**"""
        await event.edit(profile_text, buttons=back_button)

    elif action == "shop_menu":
        shop_text = """**🛒 المتجر** 🛒

**في المتجر، يمكنك استخدام نقاطك التي جمعتها من التفاعل لشراء امتيازات خاصة ومؤقتة، مثل:**
- **لقب VIP:** **يضيف علامة مميزة لملفك الشخصي.**
- **حصانة:** **تحميك من الأوامر التفاعلية المزعجة.**"""
        await event.edit(shop_text, buttons=back_button)

    elif action == "protection_menu":
        protection_text = """**🛡️ قسم الحماية** 🛡️

**هذا القسم للمشرفين فقط، ويوفر أدوات قوية لحماية المجموعة من الرسائل المزعجة والمخالفات، ويشمل:**
- **قفل وفتح الوسائط (الصور، الروابط، التوجيه...).**
- **أوامر الكتم والحظر والتحذير.**
- **فلتر الكلمات الممنوعة.**"""
        await event.edit(protection_text, buttons=back_button)
        
    elif action == "tools_menu":
        tools_text = """**🛠️ قسم أدوات المجموعة** 🛠️

**أدوات خدمية متنوعة ومفيدة لجميع أعضاء المجموعة، مثل:**
- **`عمري`**: **لحساب عمرك بدقة.**
- **`طقس`**: **لمعرفة حالة الطقس.**
- **`ويكي`**: **للبحث في موسوعة ويكيبيديا.**
- **`ترجم`**: **لترجمة النصوص.**
- **`وقت`**: **لمعرفة التوقيت العالمي.**
- **`احجي`**: **لتحويل النص إلى بصمة صوتية.**"""
        await event.edit(tools_text, buttons=back_button)

    elif action == "services_menu":
        services_text = """**🕌 قسم الخدمات الدينية** 🕌

**يحتوي هذا القسم على خدمات دينية متنوعة، مثل:**
- **`اذان`**: **لعرض مواقيت الصلاة.**
- **`سيرة النبي`**: **لعرض مراحل من سيرة النبي محمد ﷺ.**
- **`اسماء الله الحسنى`**: **لعرض أسماء الله الحسنى مع شرحها.**
- **`سبحة`**: **سبحة إلكترونية تفاعلية.**
- **`اذكار الصباح`** و **`اذكار المساء`.**"""
        await event.edit(services_text, buttons=back_button)
    
    elif action == "replies_menu":
        replies_text = """**💬 قسم الردود** 💬

**هذا القسم للمشرفين، ويسمح لهم بتخصيص ردود البوت:**
- **`اضف رد`**: **لإضافة ردود تلقائية مخصصة.**
- **`حذف رد`**: **لحذف رد معين.**
- **تخصيص ردود المناداة على البوت والمطور.**"""
        await event.edit(replies_text, buttons=back_button)

    elif action == "back_to_main":
        start_text, buttons = await get_main_private_menu()
        await event.edit(start_text, buttons=buttons)

@client.on(events.NewMessage(func=lambda e: e.is_private))
async def private_fallback_handler(event):
    known_commands = ["/start", "الاوامر", "بوت", "هلو", "السلام عليكم", "مرحبا", "/صراحة", "اعتراف"]
    if any(event.text.lower().startswith(cmd) for cmd in known_commands):
        return
    return
