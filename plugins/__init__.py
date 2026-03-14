import importlib
import logging

logger = logging.getLogger(__name__)

# قائمة الإضافات التي يتم تحميلها
ALL_MODULES = [
    "plugins.utils",
    "plugins.core",
    "plugins.events",
    "plugins.auto_messages",
    "plugins.callbacks",
    "plugins.interactive_callbacks",
    "plugins.cleaning",
    "plugins.admin",
    "plugins.tagging",
    "plugins.aliases",
    "plugins.dictionary",
    "plugins.achievements",
    "plugins.fun",
    "plugins.games",
    "plugins.animal",
    "plugins.animations",
    "plugins.fast_games",
    "plugins.replies",
    "plugins.default_replies",
    "plugins.services",
    "plugins.tools",
    "plugins.poll",
    "plugins.web_tools",
    "plugins.confess",
    "plugins.private",
    "plugins.profile",
    "plugins.shop",
    "plugins.quiz_data",
    "plugins.id",
    "plugins.developer",
    "plugins.game_data",
    "plugins.ai",
    "plugins.menu_commands",
    "plugins.contact",
    "plugins.millionaire_data",
    "plugins.millionaire",
    "plugins.owner",
    "plugins.sudo_panel",
    "plugins.media_search",
    "plugins.custom_commands",
    "plugins.admin_menus",
    "plugins.settings",
    "plugins.leaderboard",
    "plugins.message_logger",
    "plugins.analytics",
    "plugins.raid_mode",
    "plugins.afk",
    "plugins.socials",
    "plugins.islamic_quiz_data",
    "plugins.islamic_quiz",
    "plugins.user_info",
    "plugins.link",
]

def load_plugins(client):
    """
    تحميل الإضافات الموجودة في قائمة ALL_MODULES لمكتبة Telethon
    """
    loaded_count = 0
    for module_name in ALL_MODULES:
        try:
            # استيراد الوحدة بناءً على الاسم الموجود في القائمة
            importlib.import_module(module_name)
            logger.info(f"✅ تم تحميل الإضافة: {module_name}")
            loaded_count += 1
        except Exception as e:
            logger.error(f"❌ فشل تحميل الإضافة {module_name}: {e}")
    
    logger.info(f"📊 إجمالي الإضافات المحملة بنجاح: {loaded_count}")
