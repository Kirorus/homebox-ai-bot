"""
Settings handling logic
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from .base_handler import BaseHandler
from models.user import UserSettings
from bot.keyboards import KeyboardManager
from i18n.i18n_manager import t

logger = logging.getLogger(__name__)


class SettingsHandler(BaseHandler):
    """Handles settings-related commands"""
    
    def __init__(self, settings, database):
        super().__init__(settings, database)
        self.keyboard_manager = KeyboardManager()
        self.register_handlers()
    
    def register_handlers(self):
        """Register settings-related handlers"""
        
        @self.router.message(Command("settings"))
        async def cmd_settings(message: Message, state: FSMContext):
            """Handle /settings command"""
            try:
                await self.log_user_action("settings_command", message.from_user.id)
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    await message.answer(t('en', 'errors.access_denied'))
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                settings_text = (
                    f"⚙️ **{t(bot_lang, 'settings.title')}**\n\n"
                    f"🤖 **{t(bot_lang, 'settings.bot_lang')}:** {user_settings.bot_lang.upper()}\n"
                    f"📝 **{t(bot_lang, 'settings.gen_lang')}:** {user_settings.gen_lang.upper()}\n"
                    f"🧠 **{t(bot_lang, 'settings.model')}:** `{user_settings.model}`\n\n"
                    f"{t(bot_lang, 'settings.what_change')}"
                )
                
                await message.answer(
                    settings_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await self.handle_error(e, "settings command", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.message(Command("help"))
        async def cmd_help(message: Message, state: FSMContext):
            """Handle /help command"""
            try:
                await self.log_user_action("help_command", message.from_user.id)
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    await message.answer(t('en', 'errors.access_denied'))
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                help_text = f"""
❓ **{t(bot_lang, 'help.title')}**

**{t(bot_lang, 'help.how_to_use')}**
1️⃣ {t(bot_lang, 'help.step1')}
2️⃣ {t(bot_lang, 'help.step2')}
3️⃣ {t(bot_lang, 'help.step3')}
4️⃣ {t(bot_lang, 'help.step4')}

**{t(bot_lang, 'help.features')}**
• 🧠 {t(bot_lang, 'help.ai_analysis')}
• 📍 {t(bot_lang, 'help.auto_location')}
• 🔄 {t(bot_lang, 'help.reanalysis')}
• 🌍 {t(bot_lang, 'help.multi_lang')}

**{t(bot_lang, 'help.tips')}**
• {t(bot_lang, 'help.tip1')}
• {t(bot_lang, 'help.tip2')}
• {t(bot_lang, 'help.tip3')}

**{t(bot_lang, 'help.commands')}**
• /start - {t(bot_lang, 'help.start_desc')}
• /settings - {t(bot_lang, 'help.settings_desc')}
• /stats - {t(bot_lang, 'help.stats_desc')}
• /search - {t(bot_lang, 'help.search_desc')}
• /recent - {t(bot_lang, 'help.recent_desc')}
• /test_items - {t(bot_lang, 'help.test_items_desc')}
• /test_search - {t(bot_lang, 'help.test_search_desc')}
• /help - {t(bot_lang, 'help.help_desc')}
                """.strip()
                
                await message.answer(
                    help_text,
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await self.handle_error(e, "help command", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.message(Command("stats"))
        async def cmd_stats(message: Message, state: FSMContext):
            """Handle /stats command"""
            try:
                await self.log_user_action("stats_command", message.from_user.id)
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    await message.answer(t('en', 'errors.access_denied'))
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get bot and user statistics
                bot_stats = await self.database.get_bot_stats()
                user_stats = await self.database.get_user_stats(message.from_user.id)
                
                # Create detailed stats message
                stats_text = self.create_detailed_stats_message(
                    bot_lang, bot_stats, user_stats, user_settings.to_dict()
                )
                
                await message.answer(
                    stats_text,
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await self.handle_error(e, "stats command", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "settings_bot_lang")
        async def settings_bot_lang_callback(callback: CallbackQuery, state: FSMContext):
            """Handle bot language settings"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                await callback.message.edit_text(
                    f"🤖 **{t(bot_lang, 'settings.bot_lang_title')}**\n\n{t(bot_lang, 'settings.bot_lang_prompt')}",
                    reply_markup=self.keyboard_manager.bot_lang_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "bot_lang_settings", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "settings_gen_lang")
        async def settings_gen_lang_callback(callback: CallbackQuery, state: FSMContext):
            """Handle generation language settings"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                await callback.message.edit_text(
                    f"📝 **{t(bot_lang, 'settings.gen_lang_title')}**\n\n{t(bot_lang, 'settings.gen_lang_prompt')}",
                    reply_markup=self.keyboard_manager.gen_lang_keyboard(user_settings.gen_lang),
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "gen_lang_settings", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "settings_model")
        async def settings_model_callback(callback: CallbackQuery, state: FSMContext):
            """Handle model selection settings"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                available_models = self.settings.ai.available_models
                current_model = user_settings.model
                
                await callback.message.edit_text(
                    f"🧠 **{t(bot_lang, 'settings.model')}**\n\n{t(bot_lang, 'settings.current_model')}: `{current_model}`\n\n{t(bot_lang, 'settings.choose_model_prompt')}",
                    reply_markup=self.keyboard_manager.models_keyboard(current_model, available_models, bot_lang),
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "model_settings", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "bot_lang_ru")
        async def set_bot_lang_ru_callback(callback: CallbackQuery, state: FSMContext):
            """Set bot language to Russian"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.bot_lang = 'ru'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t('ru', 'success.bot_lang_set_ru')}**\n\n{t('ru', 'settings.bot_lang_prompt')}",
                    reply_markup=self.keyboard_manager.bot_lang_keyboard('ru'),
                    parse_mode="Markdown"
                )
                await callback.answer(t('ru', 'success.language_updated'))
                await self.log_user_action("bot_lang_changed", callback.from_user.id, {"new_lang": "ru"})
                
            except Exception as e:
                await self.handle_error(e, "set_bot_lang_ru", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "bot_lang_en")
        async def set_bot_lang_en_callback(callback: CallbackQuery, state: FSMContext):
            """Set bot language to English"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.bot_lang = 'en'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t('en', 'success.bot_lang_set_en')}**\n\n{t('en', 'settings.bot_lang_prompt')}",
                    reply_markup=self.keyboard_manager.bot_lang_keyboard('en'),
                    parse_mode="Markdown"
                )
                await callback.answer(t('en', 'success.language_updated'))
                await self.log_user_action("bot_lang_changed", callback.from_user.id, {"new_lang": "en"})
                
            except Exception as e:
                await self.handle_error(e, "set_bot_lang_en", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "bot_lang_de")
        async def set_bot_lang_de_callback(callback: CallbackQuery, state: FSMContext):
            """Set bot language to German"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                logger.info(f"Before change - user settings: {user_settings.to_dict()}")
                
                user_settings.bot_lang = 'de'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                # Verify the change was saved
                updated_settings = await self.get_user_settings(callback.from_user.id)
                logger.info(f"After change - user settings: {updated_settings.to_dict()}")
                logger.info(f"Language changed to: {updated_settings.bot_lang} for user {callback.from_user.id}")
                
                await callback.message.edit_text(
                    f"✅ **{t('de', 'success.bot_lang_set_de')}**\n\n{t('de', 'settings.bot_lang_prompt')}",
                    reply_markup=self.keyboard_manager.bot_lang_keyboard('de'),
                    parse_mode="Markdown"
                )
                await callback.answer(t('de', 'success.language_updated'))
                await self.log_user_action("bot_lang_changed", callback.from_user.id, {"new_lang": "de"})
                
            except Exception as e:
                await self.handle_error(e, "set_bot_lang_de", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "gen_lang_ru")
        async def set_gen_lang_ru_callback(callback: CallbackQuery, state: FSMContext):
            """Set generation language to Russian"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.gen_lang = 'ru'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.gen_lang_set_ru')}**\n\n{t(user_settings.bot_lang, 'settings.gen_lang_prompt')}",
                    reply_markup=self.keyboard_manager.gen_lang_keyboard('ru'),
                    parse_mode="Markdown"
                )
                await callback.answer(t(user_settings.bot_lang, 'success.language_updated'))
                await self.log_user_action("gen_lang_changed", callback.from_user.id, {"new_lang": "ru"})
                
            except Exception as e:
                await self.handle_error(e, "set_gen_lang_ru", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "gen_lang_en")
        async def set_gen_lang_en_callback(callback: CallbackQuery, state: FSMContext):
            """Set generation language to English"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.gen_lang = 'en'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.gen_lang_set_en')}**\n\n{t(user_settings.bot_lang, 'settings.gen_lang_prompt')}",
                    reply_markup=self.keyboard_manager.gen_lang_keyboard('en'),
                    parse_mode="Markdown"
                )
                await callback.answer(t(user_settings.bot_lang, 'success.language_updated'))
                await self.log_user_action("gen_lang_changed", callback.from_user.id, {"new_lang": "en"})
                
            except Exception as e:
                await self.handle_error(e, "set_gen_lang_en", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "gen_lang_de")
        async def set_gen_lang_de_callback(callback: CallbackQuery, state: FSMContext):
            """Set generation language to German"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.gen_lang = 'de'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.gen_lang_set_de')}**\n\n{t(user_settings.bot_lang, 'settings.gen_lang_prompt')}",
                    reply_markup=self.keyboard_manager.gen_lang_keyboard('de'),
                    parse_mode="Markdown"
                )
                await callback.answer(t(user_settings.bot_lang, 'success.language_updated'))
                await self.log_user_action("gen_lang_changed", callback.from_user.id, {"new_lang": "de"})
                
            except Exception as e:
                await self.handle_error(e, "set_gen_lang_de", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "bot_lang_fr")
        async def set_bot_lang_fr_callback(callback: CallbackQuery, state: FSMContext):
            """Set bot language to French"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.bot_lang = 'fr'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t('fr', 'success.bot_lang_set_fr')}**\n\n{t('fr', 'settings.bot_lang_prompt')}",
                    reply_markup=self.keyboard_manager.bot_lang_keyboard('fr'),
                    parse_mode="Markdown"
                )
                await callback.answer(t('fr', 'success.language_updated'))
                await self.log_user_action("bot_lang_changed", callback.from_user.id, {"new_lang": "fr"})
                
            except Exception as e:
                await self.handle_error(e, "set_bot_lang_fr", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "bot_lang_es")
        async def set_bot_lang_es_callback(callback: CallbackQuery, state: FSMContext):
            """Set bot language to Spanish"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.bot_lang = 'es'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t('es', 'success.bot_lang_set_es')}**\n\n{t('es', 'settings.bot_lang_prompt')}",
                    reply_markup=self.keyboard_manager.bot_lang_keyboard('es'),
                    parse_mode="Markdown"
                )
                await callback.answer(t('es', 'success.language_updated'))
                await self.log_user_action("bot_lang_changed", callback.from_user.id, {"new_lang": "es"})
                
            except Exception as e:
                await self.handle_error(e, "set_bot_lang_es", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "gen_lang_fr")
        async def set_gen_lang_fr_callback(callback: CallbackQuery, state: FSMContext):
            """Set generation language to French"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.gen_lang = 'fr'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.gen_lang_set_fr')}**\n\n{t(user_settings.bot_lang, 'settings.gen_lang_prompt')}",
                    reply_markup=self.keyboard_manager.gen_lang_keyboard('fr'),
                    parse_mode="Markdown"
                )
                await callback.answer(t(user_settings.bot_lang, 'success.language_updated'))
                await self.log_user_action("gen_lang_changed", callback.from_user.id, {"new_lang": "fr"})
                
            except Exception as e:
                await self.handle_error(e, "set_gen_lang_fr", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "gen_lang_es")
        async def set_gen_lang_es_callback(callback: CallbackQuery, state: FSMContext):
            """Set generation language to Spanish"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.gen_lang = 'es'
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.gen_lang_set_es')}**\n\n{t(user_settings.bot_lang, 'settings.gen_lang_prompt')}",
                    reply_markup=self.keyboard_manager.gen_lang_keyboard('es'),
                    parse_mode="Markdown"
                )
                await callback.answer(t(user_settings.bot_lang, 'success.language_updated'))
                await self.log_user_action("gen_lang_changed", callback.from_user.id, {"new_lang": "es"})
                
            except Exception as e:
                await self.handle_error(e, "set_gen_lang_es", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("model_"))
        async def set_model_callback(callback: CallbackQuery, state: FSMContext):
            """Set AI model"""
            try:
                # Extract model name from callback data
                model_name = callback.data.split("_", 1)[1]
                
                # Validate model
                if model_name not in self.settings.ai.available_models:
                    await callback.answer(t('en', 'errors.invalid_model'), show_alert=True)
                    return
                
                user_settings = await self.get_user_settings(callback.from_user.id)
                user_settings.model = model_name
                await self.database.set_user_settings(callback.from_user.id, user_settings.to_dict())
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.model_set')}: `{model_name}`**\n\n{t(user_settings.bot_lang, 'settings.what_change')}",
                    reply_markup=self.keyboard_manager.settings_main_keyboard(user_settings.bot_lang),
                    parse_mode="Markdown"
                )
                await callback.answer(t(user_settings.bot_lang, 'success.model_updated'))
                await self.log_user_action("model_changed", callback.from_user.id, {"new_model": model_name})
                
            except Exception as e:
                await self.handle_error(e, "set_model", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("model_page_"))
        async def model_page_callback(callback: CallbackQuery, state: FSMContext):
            """Handle model pagination"""
            try:
                # Extract page number from callback data
                page = int(callback.data.split("_")[-1])
                
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                available_models = self.settings.ai.available_models
                current_model = user_settings.model
                
                # Validate page number
                page_size = 10
                max_pages = (len(available_models) + page_size - 1) // page_size
                if page < 0 or page >= max_pages:
                    await callback.answer(t(bot_lang, 'errors.invalid_model'), show_alert=True)
                    return
                
                await callback.message.edit_text(
                    f"🧠 **{t(bot_lang, 'settings.model')}**\n\n{t(bot_lang, 'settings.current_model')}: `{current_model}`\n\n{t(bot_lang, 'settings.choose_model_prompt')}",
                    reply_markup=self.keyboard_manager.models_keyboard(current_model, available_models, bot_lang, page),
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except ValueError as e:
                logger.error(f"Invalid page number in model_page callback: {callback.data}")
                await callback.answer(t('en', 'errors.invalid_model'), show_alert=True)
            except Exception as e:
                await self.handle_error(e, "model_page", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "quick_stats")
        async def quick_stats_callback(callback: CallbackQuery, state: FSMContext):
            """Show detailed statistics"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get bot and user statistics
                bot_stats = await self.database.get_bot_stats()
                user_stats = await self.database.get_user_stats(callback.from_user.id)
                
                # Create detailed stats message
                stats_text = self.create_detailed_stats_message(
                    bot_lang, bot_stats, user_stats, user_settings.to_dict()
                )
                
                await callback.message.edit_text(
                    stats_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "quick_stats", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "quick_restart")
        async def quick_restart_callback(callback: CallbackQuery, state: FSMContext):
            """Restart bot (placeholder)"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                await callback.answer(t(bot_lang, 'restart.not_implemented'), show_alert=True)
                
            except Exception as e:
                await self.handle_error(e, "quick_restart", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        
        @self.router.callback_query(F.data == "back_to_settings")
        async def back_to_settings_callback(callback: CallbackQuery, state: FSMContext):
            """Return to main settings menu"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                logger.info(f"Back to settings - current language: {bot_lang} for user {callback.from_user.id}")
                logger.info(f"User settings: {user_settings.to_dict()}")
                
                # Test translation before using it
                test_translation = t(bot_lang, 'settings.what_change')
                logger.info(f"Translation test for {bot_lang}: {test_translation}")
                
                settings_text = (
                    f"⚙️ **{t(bot_lang, 'settings.title')}**\n\n"
                    f"🤖 **{t(bot_lang, 'settings.bot_lang')}:** {user_settings.bot_lang.upper()}\n"
                    f"📝 **{t(bot_lang, 'settings.gen_lang')}:** {user_settings.gen_lang.upper()}\n"
                    f"🧠 **{t(bot_lang, 'settings.model')}:** `{user_settings.model}`\n\n"
                    f"{t(bot_lang, 'settings.what_change')}"
                )
                
                await callback.message.edit_text(
                    settings_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "back_to_settings", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)