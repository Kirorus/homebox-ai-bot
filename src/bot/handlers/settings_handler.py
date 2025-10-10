"""
Settings handling logic
"""

import logging
import subprocess
import os
import sys
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .base_handler import BaseHandler
from models.user import UserSettings
from bot.keyboards import KeyboardManager
from bot.states import LocationStates
from i18n.i18n_manager import t

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown parsing"""
    if not text:
        return text
    # Escape characters that have special meaning in Markdown
    return text.replace('\\', '\\\\').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')


def escape_html(text: str) -> str:
    """Escape special characters for HTML parsing"""
    if not text:
        return text
    # Escape characters that have special meaning in HTML
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class SettingsHandler(BaseHandler):
    """Handles settings-related commands"""
    
    def __init__(self, settings, database, homebox_service):
        super().__init__(settings, database)
        self.homebox_service = homebox_service
        self.keyboard_manager = KeyboardManager()
        self.register_handlers()
    
    def register_handlers(self):
        """Register settings-related handlers"""
        
        @self.router.callback_query(F.data == "open_settings")
        async def open_settings_callback(callback: CallbackQuery, state: FSMContext):
            """Open settings from main menu"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                model_name = escape_html(user_settings.model)
                settings_text = (
                    f"⚙️ <b>{t(bot_lang, 'settings.title')}</b>\n\n"
                    f"🤖 <b>{t(bot_lang, 'settings.bot_lang')}:</b> {user_settings.bot_lang.upper()}\n"
                    f"📝 <b>{t(bot_lang, 'settings.gen_lang')}:</b> {user_settings.gen_lang.upper()}\n"
                    f"🧠 <b>{t(bot_lang, 'settings.model')}:</b> <code>{model_name}</code>\n\n"
                    f"{t(bot_lang, 'settings.what_change')}"
                )
                await callback.message.edit_text(
                    settings_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="HTML"
                )
                await callback.answer()
            except Exception as e:
                await self.handle_error(e, "open_settings callback", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))

        @self.router.callback_query(F.data == "open_help")
        async def open_help_callback(callback: CallbackQuery, state: FSMContext):
            """Open help from main menu"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
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
• /help - {t(bot_lang, 'help.help_desc')}
                """.strip()
                await callback.message.edit_text(help_text, parse_mode="Markdown")
                await callback.answer()
            except Exception as e:
                await self.handle_error(e, "open_help callback", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))

        @self.router.callback_query(F.data == "generate_location_descriptions")
        async def start_description_generation(callback: CallbackQuery, state: FSMContext):
            """Start location description generation process"""
            logger.info("start_description_generation handler called")
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get all locations
                all_locations = await self.homebox_service.get_locations()
                if not all_locations:
                    await callback.answer(t(bot_lang, 'errors.no_locations'))
                    return
                
                # Filter locations with [TGB] marker
                marked_locations = [loc for loc in all_locations if '[TGB]' in (loc.description or '')]
                
                if not marked_locations:
                    await callback.answer(t(bot_lang, 'locations.no_marked_locations'), show_alert=True)
                    return
                
                # Store data in state
                await state.set_data({
                    'all_locations': all_locations,
                    'marked_locations': marked_locations,
                    'current_page': 0
                })
                
                text = t(bot_lang, 'locations.select_for_description')
                keyboard = self.keyboard_manager.location_description_selection_keyboard(all_locations, bot_lang, 0)
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.set_state(LocationStates.selecting_locations_for_description)
                logger.info(f"State set to: {LocationStates.selecting_locations_for_description}")
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "start_description_generation", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        # Handlers for location description generation (registered at init, not nested)
        @self.router.callback_query(F.data.startswith("generate_desc_"))
        async def generate_location_description_cb(callback: CallbackQuery, state: FSMContext):
            """Generate description for selected location (robust registration)"""
            logger.info(f"generate_location_description (robust) with data: {callback.data}")
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                location_id = callback.data.replace("generate_desc_", "")
                data = await state.get_data()
                all_locations = data.get('all_locations') or []
                selected_location = next((loc for loc in all_locations if str(loc.id) == location_id), None)
                if not selected_location:
                    try:
                        await callback.answer(t(bot_lang, 'errors.location_not_found'), show_alert=True)
                    except Exception:
                        pass
                    return
                # Show generating message and stop spinner
                try:
                    await callback.answer()
                except Exception:
                    pass
                generating_msg = await callback.message.edit_text(
                    t(bot_lang, 'locations.generating_description').format(location_name=selected_location.name)
                )
                try:
                    items = await self.homebox_service.get_items_by_location(selected_location.id)
                    if not items:
                        await generating_msg.edit_text(
                            t(bot_lang, 'locations.no_items_in_location').format(location_name=selected_location.name),
                            parse_mode="Markdown"
                        )
                        return
                    item_names = [item.name for item in items[:10]]
                    item_list = ", ".join(item_names)
                    prompt = (
                        f"Based on the location name \"{selected_location.name}\" and the items stored there: {item_list}, "
                        f"generate a brief, descriptive text (2-3 sentences) that describes what this location is used for "
                        f"and what kind of items are typically stored there. The description should be practical and helpful for organizing purposes."
                    )
                    generated_description = await self.ai_service.generate_text(prompt)
                    if not generated_description:
                        await generating_msg.edit_text(
                            t(bot_lang, 'locations.description_generation_failed').format(
                                location_name=selected_location.name,
                                error="AI service unavailable"
                            ),
                            parse_mode="Markdown"
                        )
                        return
                    await state.update_data({
                        'selected_location': selected_location,
                        'generated_description': generated_description
                    })
                    current_desc = selected_location.description or t(bot_lang, 'common.no_description')
                    if '[TGB]' in current_desc:
                        current_desc = current_desc.replace('[TGB]', '').strip()
                    confirm_text = t(bot_lang, 'locations.confirm_update_description').format(
                        location_name=selected_location.name,
                        current_description=current_desc,
                        new_description=generated_description
                    )
                    keyboard = self.keyboard_manager.description_confirmation_keyboard(bot_lang)
                    await generating_msg.edit_text(
                        confirm_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    await state.set_state(LocationStates.confirming_description_update)
                except Exception as e:
                    await generating_msg.edit_text(
                        t(bot_lang, 'locations.description_generation_failed').format(
                            location_name=selected_location.name,
                            error=str(e)
                        ),
                        parse_mode="Markdown"
                    )
            except Exception as e:
                await self.handle_error(e, "generate_location_description_cb", callback.from_user.id)
                try:
                    await callback.answer(t('en', 'errors.occurred'))
                except Exception:
                    pass

        @self.router.callback_query(F.data == "confirm_description_update")
        async def confirm_description_update_cb(callback: CallbackQuery, state: FSMContext):
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                data = await state.get_data()
                selected_location = data.get('selected_location')
                generated_description = data.get('generated_description')
                if not selected_location or not generated_description:
                    try:
                        await callback.answer(t('en', 'errors.occurred'))
                    except Exception:
                        pass
                    return
                current_desc = selected_location.description or ''
                new_description = f"{generated_description} [TGB]" if '[TGB]' in current_desc else generated_description
                success = await self.homebox_service.update_location(selected_location.id, {
                    'description': new_description
                })
                result_text = (
                    t(bot_lang, 'locations.description_updated').format(location_name=selected_location.name)
                    if success else
                    t(bot_lang, 'locations.description_generation_failed').format(location_name=selected_location.name, error="Failed to update location")
                )
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")
                await state.clear()
                try:
                    await callback.answer()
                except Exception:
                    pass
            except Exception as e:
                await self.handle_error(e, "confirm_description_update_cb", callback.from_user.id)
                try:
                    await callback.answer(t('en', 'errors.occurred'))
                except Exception:
                    pass

        @self.router.callback_query(F.data == "reject_description_update")
        async def reject_description_update_cb(callback: CallbackQuery, state: FSMContext):
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                await callback.message.edit_text(
                    t(bot_lang, 'locations.description_generation_cancelled'),
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await state.clear()
                try:
                    await callback.answer()
                except Exception:
                    pass
            except Exception as e:
                await self.handle_error(e, "reject_description_update_cb", callback.from_user.id)
                try:
                    await callback.answer(t('en', 'errors.occurred'))
                except Exception:
                    pass

        @self.router.callback_query(F.data == "regenerate_description")
        async def regenerate_description_cb(callback: CallbackQuery, state: FSMContext):
            try:
                data = await state.get_data()
                selected_location = data.get('selected_location')
                if not selected_location:
                    try:
                        await callback.answer(t('en', 'errors.occurred'))
                    except Exception:
                        pass
                    return
                # Reuse generation logic
                callback.data = f"generate_desc_{selected_location.id}"
                await generate_location_description_cb(callback, state)
            except Exception as e:
                await self.handle_error(e, "regenerate_description_cb", callback.from_user.id)
                try:
                    await callback.answer(t('en', 'errors.occurred'))
                except Exception:
                    pass

        @self.router.callback_query(F.data == "cancel_description_generation")
        async def cancel_description_generation_cb(callback: CallbackQuery, state: FSMContext):
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                await callback.message.edit_text(
                    t(bot_lang, 'locations.description_generation_cancelled'),
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await state.clear()
                try:
                    await callback.answer()
                except Exception:
                    pass
            except Exception as e:
                await self.handle_error(e, "cancel_description_generation_cb", callback.from_user.id)
                try:
                    await callback.answer(t('en', 'errors.occurred'))
                except Exception:
                    pass
        
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
                
                # Escape special characters in model name for HTML
                model_name = escape_html(user_settings.model)
                
                settings_text = (
                    f"⚙️ <b>{t(bot_lang, 'settings.title')}</b>\n\n"
                    f"🤖 <b>{t(bot_lang, 'settings.bot_lang')}:</b> {user_settings.bot_lang.upper()}\n"
                    f"📝 <b>{t(bot_lang, 'settings.gen_lang')}:</b> {user_settings.gen_lang.upper()}\n"
                    f"🧠 <b>{t(bot_lang, 'settings.model')}:</b> <code>{model_name}</code>\n\n"
                    f"{t(bot_lang, 'settings.what_change')}"
                )
                
                await message.answer(
                    settings_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="HTML"
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
        
        @self.router.message(Command("myid", "id"))
        async def cmd_myid(message: Message, state: FSMContext):
            """Handle /myid and /id commands - show user ID (works for all users)"""
            try:
                await self.log_user_action("myid_command", message.from_user.id)
                
                # Get user info
                user = message.from_user
                user_id = user.id
                username = user.username or "Not set"
                first_name = user.first_name or "Not set"
                last_name = user.last_name or "Not set"
                
                # Create response message
                response_text = (
                    f"🆔 **Your Telegram Information:**\n\n"
                    f"**User ID:** `{user_id}`\n"
                    f"**Username:** @{username}\n"
                    f"**First Name:** {first_name}\n"
                    f"**Last Name:** {last_name}\n\n"
                    f"Use this ID to add yourself to the bot's allowed users list."
                )
                
                await message.answer(response_text, parse_mode="Markdown")
                
            except Exception as e:
                await self.handle_error(e, "myid command", message.from_user.id)
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
                
                # Escape special characters in model name for Markdown
                escaped_model = escape_markdown(current_model)
                
                await callback.message.edit_text(
                    f"🧠 **{t(bot_lang, 'settings.model')}**\n\n{t(bot_lang, 'settings.current_model')}: `{escaped_model}`\n\n{t(bot_lang, 'settings.choose_model_prompt')}",
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
                
                # Escape special characters in model name for Markdown
                escaped_model = escape_markdown(model_name)
                
                await callback.message.edit_text(
                    f"✅ **{t(user_settings.bot_lang, 'success.model_set')}: `{escaped_model}`**\n\n{t(user_settings.bot_lang, 'settings.what_change')}",
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
                
                # Escape special characters in model name for Markdown
                escaped_model = escape_markdown(current_model)
                
                await callback.message.edit_text(
                    f"🧠 **{t(bot_lang, 'settings.model')}**\n\n{t(bot_lang, 'settings.current_model')}: `{escaped_model}`\n\n{t(bot_lang, 'settings.choose_model_prompt')}",
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
            """Show restart confirmation dialog"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Show confirmation dialog
                confirm_text = (
                    f"**{t(bot_lang, 'restart.confirm_title')}**\n\n"
                    f"{t(bot_lang, 'restart.confirm_message')}"
                )
                
                keyboard = self.keyboard_manager.restart_confirmation_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    confirm_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "quick_restart", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "confirm_restart")
        async def confirm_restart_callback(callback: CallbackQuery, state: FSMContext):
            """Confirm and execute bot restart"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Log the restart action first
                await self.log_user_action("bot_restart", callback.from_user.id, {"user_id": callback.from_user.id})
                
                # Execute restart script
                try:
                    # Get the project root directory (go up from handlers/settings_handler.py -> handlers -> bot -> src -> project_root)
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
                    restart_script = os.path.join(project_root, "src", "restart_bot.sh")
                    
                    logger.info(f"Current dir: {current_dir}")
                    logger.info(f"Project root: {project_root}")
                    logger.info(f"Restart script path: {restart_script}")
                    logger.info(f"Script exists: {os.path.exists(restart_script)}")
                    
                    # Check if script exists
                    if not os.path.exists(restart_script):
                        raise FileNotFoundError(f"Restart script not found: {restart_script}")
                    
                    # Make sure script is executable
                    os.chmod(restart_script, 0o755)
                    
                    # Send restarting message first
                    await callback.message.edit_text(
                        f"**{t(bot_lang, 'restart.restarting')}**",
                        parse_mode="Markdown"
                    )
                    
                    # Give time for message to be sent
                    import asyncio
                    await asyncio.sleep(0.5)
                    
                    # Execute restart script in background
                    logger.info("Starting restart script...")
                    process = subprocess.Popen([restart_script], cwd=project_root)
                    logger.info(f"Restart script started with PID: {process.pid}")
                    
                    # Give a bit more time for the script to start
                    await asyncio.sleep(1)
                    
                    # Stop the bot gracefully instead of sys.exit()
                    logger.info("Bot restart initiated successfully")
                    # We'll let the restart script handle the process termination
                    # This avoids the SystemExit exception in the event loop
                    
                except Exception as restart_error:
                    logger.error(f"Failed to restart bot: {restart_error}")
                    # Escape special characters for HTML
                    error_msg = str(restart_error).replace('<', '&lt;').replace('>', '&gt;')
                    try:
                        await callback.message.edit_text(
                            f"<b>{t(bot_lang, 'restart.error')}</b>: {error_msg}",
                            parse_mode="HTML"
                        )
                    except Exception as msg_error:
                        # If we can't send the error message, just log it
                        logger.error(f"Failed to send error message: {msg_error}")
                
            except Exception as e:
                await self.handle_error(e, "confirm_restart", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "cancel_restart")
        async def cancel_restart_callback(callback: CallbackQuery, state: FSMContext):
            """Cancel restart and return to settings"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Return to main settings menu
                model_name = escape_html(user_settings.model)
                
                settings_text = (
                    f"⚙️ <b>{t(bot_lang, 'settings.title')}</b>\n\n"
                    f"🤖 <b>{t(bot_lang, 'settings.bot_lang')}:</b> {user_settings.bot_lang.upper()}\n"
                    f"📝 <b>{t(bot_lang, 'settings.gen_lang')}:</b> {user_settings.gen_lang.upper()}\n"
                    f"🧠 <b>{t(bot_lang, 'settings.model')}:</b> <code>{model_name}</code>\n\n"
                    f"{t(bot_lang, 'settings.what_change')}"
                )
                
                await callback.message.edit_text(
                    settings_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="HTML"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "cancel_restart", callback.from_user.id)
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
                
                # Escape special characters in model name for HTML
                model_name = escape_html(user_settings.model)
                
                settings_text = (
                    f"⚙️ <b>{t(bot_lang, 'settings.title')}</b>\n\n"
                    f"🤖 <b>{t(bot_lang, 'settings.bot_lang')}:</b> {user_settings.bot_lang.upper()}\n"
                    f"📝 <b>{t(bot_lang, 'settings.gen_lang')}:</b> {user_settings.gen_lang.upper()}\n"
                    f"🧠 <b>{t(bot_lang, 'settings.model')}:</b> <code>{model_name}</code>\n\n"
                    f"{t(bot_lang, 'settings.what_change')}"
                )
                
                await callback.message.edit_text(
                    settings_text,
                    reply_markup=self.keyboard_manager.settings_main_keyboard(bot_lang),
                    parse_mode="HTML"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "back_to_settings", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "location_management")
        async def location_management_callback(callback: CallbackQuery, state: FSMContext):
            """Handle location management callback"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                text = t(bot_lang, 'locations.management_menu')
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "location_management", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "mark_locations")
        async def start_location_marking(callback: CallbackQuery, state: FSMContext):
            """Start location marking process"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get all locations
                all_locations = await self.homebox_service.get_locations()
                if not all_locations:
                    await callback.answer(t(bot_lang, 'errors.no_locations'))
                    return
                
                # Store locations and selected locations in state
                selected_locations = set()
                for loc in all_locations:
                    if '[TGB]' in (loc.description or ''):
                        selected_locations.add(str(loc.id))
                
                await state.set_data({
                    'all_locations': all_locations,
                    'selected_locations': selected_locations,
                    'current_page': 0
                })
                
                text = t(bot_lang, 'locations.select_locations')
                keyboard = self.keyboard_manager.locations_selection_keyboard(all_locations, bot_lang, 0, selected_locations=selected_locations)
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.set_state(LocationStates.selecting_locations_for_marking)
                
            except Exception as e:
                await self.handle_error(e, "start_location_marking", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data.startswith("toggle_location_"), LocationStates.selecting_locations_for_marking)
        async def toggle_location_selection(callback: CallbackQuery, state: FSMContext):
            """Toggle location selection"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                location_id = callback.data.replace("toggle_location_", "")
                data = await state.get_data()
                all_locations = data['all_locations']
                selected_locations = data['selected_locations']
                current_page = data['current_page']
                
                # Toggle selection
                if location_id in selected_locations:
                    selected_locations.remove(location_id)
                else:
                    selected_locations.add(location_id)
                
                await state.update_data(selected_locations=selected_locations)
                
                # Update keyboard
                keyboard = self.keyboard_manager.locations_selection_keyboard(all_locations, bot_lang, current_page, selected_locations=selected_locations)
                await callback.message.edit_reply_markup(reply_markup=keyboard)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "toggle_location_selection", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data.startswith("location_page_"), LocationStates.selecting_locations_for_marking)
        async def change_location_page(callback: CallbackQuery, state: FSMContext):
            """Change location selection page"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                page = int(callback.data.replace("location_page_", ""))
                data = await state.get_data()
                all_locations = data['all_locations']
                selected_locations = data['selected_locations']
                
                await state.update_data(current_page=page)
                
                keyboard = self.keyboard_manager.locations_selection_keyboard(all_locations, bot_lang, page, selected_locations=selected_locations)
                await callback.message.edit_reply_markup(reply_markup=keyboard)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "change_location_page", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "apply_location_markers", LocationStates.selecting_locations_for_marking)
        async def apply_location_markers(callback: CallbackQuery, state: FSMContext):
            """Apply location marker changes"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                data = await state.get_data()
                all_locations = data['all_locations']
                selected_locations = data['selected_locations']
                
                # Apply changes
                updated_count = 0
                errors = []
                
                for loc in all_locations:
                    has_marker = '[TGB]' in (loc.description or '')
                    should_have_marker = str(loc.id) in selected_locations
                    
                    if has_marker != should_have_marker:
                        try:
                            if should_have_marker:
                                # Add marker
                                new_description = (loc.description or '') + ' [TGB]'
                            else:
                                # Remove marker
                                new_description = (loc.description or '').replace(' [TGB]', '').replace('[TGB]', '')
                            
                            await self.homebox_service.update_location(loc.id, {'description': new_description})
                            updated_count += 1
                            
                        except Exception as e:
                            errors.append(f"{loc.name}: {str(e)}")
                
                # Show result
                if updated_count > 0:
                    if errors:
                        message = t(bot_lang, 'locations.some_errors').format(count=updated_count, errors='\n'.join(errors))
                    else:
                        message = t(bot_lang, 'locations.markers_applied').format(count=updated_count)
                else:
                    message = t(bot_lang, 'locations.no_changes')
                
                await callback.message.edit_text(message, parse_mode="Markdown")
                
                # Return to location management
                text = t(bot_lang, 'locations.management_menu')
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "apply_location_markers", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "cancel_location_marking", LocationStates.selecting_locations_for_marking)
        async def cancel_location_marking(callback: CallbackQuery, state: FSMContext):
            """Cancel location marking process"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                text = t(bot_lang, 'locations.marking_cancelled')
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "cancel_location_marking", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "view_all_locations")
        async def view_all_locations(callback: CallbackQuery, state: FSMContext):
            """View all locations with their marker status"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get all locations
                all_locations = await self.homebox_service.get_locations()
                if not all_locations:
                    await callback.answer(t(bot_lang, 'errors.no_locations'))
                    return
                
                # Count locations with and without markers
                with_markers = sum(1 for loc in all_locations if '[TGB]' in (loc.description or ''))
                without_markers = len(all_locations) - with_markers
                
                # Create detailed list of locations
                locations_list = []
                for loc in all_locations:
                    has_marker = '[TGB]' in (loc.description or '')
                    marker_icon = "✅" if has_marker else "⬜"
                    locations_list.append(f"{marker_icon} {loc.name}")
                
                # Split into pages if too long
                page_size = 20  # Number of locations per page
                total_pages = (len(locations_list) + page_size - 1) // page_size
                
                # Store in state for pagination
                await state.set_data({
                    'all_locations_list': locations_list,
                    'locations_page': 0,
                    'total_pages': total_pages,
                    'with_markers': with_markers,
                    'without_markers': without_markers
                })
                
                # Show first page
                await self.show_locations_page(callback, state, bot_lang, 0, with_markers, without_markers)
                
            except Exception as e:
                await self.handle_error(e, "view_all_locations", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data.startswith("locations_view_page_"))
        async def change_locations_view_page(callback: CallbackQuery, state: FSMContext):
            """Change locations view page"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                page = int(callback.data.replace("locations_view_page_", ""))
                data = await state.get_data()
                
                # Get original counts from when we first loaded
                with_markers = data.get('with_markers', 0)
                without_markers = data.get('without_markers', 0)
                
                await state.update_data(locations_page=page)
                
                await self.show_locations_page(callback, state, bot_lang, page, with_markers, without_markers)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "change_locations_view_page", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "back_to_location_management")
        async def back_to_location_management(callback: CallbackQuery, state: FSMContext):
            """Return to location management menu"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                text = t(bot_lang, 'locations.management_menu')
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "back_to_location_management", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
    
    async def show_locations_page(self, callback: CallbackQuery, state: FSMContext, bot_lang: str, page: int, with_markers: int, without_markers: int):
        """Show a page of locations list"""
        try:
            data = await state.get_data()
            locations_list = data.get('all_locations_list', [])
            total_pages = data.get('total_pages', 1)
            
            page_size = 20
            start = page * page_size
            end = min(start + page_size, len(locations_list))
            
            # Create page content
            page_locations = locations_list[start:end]
            locations_text = "\n".join(page_locations)
            
            # Build message text
            summary_text = t(bot_lang, 'locations.all_locations_summary').format(
                total=len(locations_list),
                with_markers=with_markers,
                without_markers=without_markers
            )
            
            if total_pages > 1:
                page_info = f"\n\n📄 {t(bot_lang, 'locations.page_info').format(page=page+1, total=total_pages)}"
            else:
                page_info = ""
            
            text = f"{summary_text}{page_info}\n\n{locations_text}"
            
            # Create keyboard
            keyboard = self.create_locations_view_keyboard(bot_lang, page, total_pages)
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            await self.handle_error(e, "show_locations_page", callback.from_user.id)
            await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data.startswith("generate_desc_"))
        async def generate_location_description(callback: CallbackQuery, state: FSMContext):
            """Generate description for selected location"""
            logger.info(f"generate_location_description handler called with data: {callback.data}")
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                location_id = callback.data.replace("generate_desc_", "")
                data = await state.get_data()
                all_locations = data['all_locations']
                
                # Find selected location
                selected_location = None
                for loc in all_locations:
                    if str(loc.id) == location_id:
                        selected_location = loc
                        break
                
                if not selected_location:
                    await callback.answer(t(bot_lang, 'errors.location_not_found'), show_alert=True)
                    return
                
                # Show generating message
                generating_msg = await callback.message.edit_text(
                    t(bot_lang, 'locations.generating_description').format(location_name=selected_location.name)
                )
                try:
                    await callback.answer()
                except Exception:
                    pass
                
                try:
                    # Get items in this location
                    items = await self.homebox_service.get_items_by_location(selected_location.id)
                    
                    if not items:
                        await generating_msg.edit_text(
                            t(bot_lang, 'locations.no_items_in_location').format(location_name=selected_location.name),
                            parse_mode="Markdown"
                        )
                        return
                    
                    # Generate description using AI
                    item_names = [item.name for item in items[:10]]  # Limit to first 10 items
                    item_list = ", ".join(item_names)
                    
                    prompt = f"""Based on the location name "{selected_location.name}" and the items stored there: {item_list}, generate a brief, descriptive text (2-3 sentences) that describes what this location is used for and what kind of items are typically stored there. The description should be practical and helpful for organizing purposes."""
                    
                    generated_description = await self.ai_service.generate_text(prompt)
                    
                    if not generated_description:
                        await generating_msg.edit_text(
                            t(bot_lang, 'locations.description_generation_failed').format(
                                location_name=selected_location.name,
                                error="AI service unavailable"
                            ),
                            parse_mode="Markdown"
                        )
                        return
                    
                    # Store generated description in state
                    await state.update_data({
                        'selected_location': selected_location,
                        'generated_description': generated_description
                    })
                    
                    # Show confirmation dialog
                    current_desc = selected_location.description or t(bot_lang, 'common.no_description')
                    if '[TGB]' in current_desc:
                        current_desc = current_desc.replace('[TGB]', '').strip()
                    
                    confirm_text = t(bot_lang, 'locations.confirm_update_description').format(
                        location_name=selected_location.name,
                        current_description=current_desc,
                        new_description=generated_description
                    )
                    
                    keyboard = self.keyboard_manager.description_confirmation_keyboard(bot_lang)
                    
                    await generating_msg.edit_text(
                        confirm_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    
                    await state.set_state(LocationStates.confirming_description_update)
                    
                except Exception as e:
                    await generating_msg.edit_text(
                        t(bot_lang, 'locations.description_generation_failed').format(
                            location_name=selected_location.name,
                            error=str(e)
                        ),
                        parse_mode="Markdown"
                    )
                
            except Exception as e:
                await self.handle_error(e, "generate_location_description", callback.from_user.id)
                try:
                    await callback.answer(t('en', 'errors.occurred'))
                except Exception:
                    pass
        
        @self.router.callback_query(F.data == "confirm_description_update", LocationStates.confirming_description_update)
        async def confirm_description_update(callback: CallbackQuery, state: FSMContext):
            """Confirm and apply description update"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                data = await state.get_data()
                selected_location = data['selected_location']
                generated_description = data['generated_description']
                
                # Update location description (preserve [TGB] marker)
                current_desc = selected_location.description or ''
                if '[TGB]' in current_desc:
                    new_description = f"{generated_description} [TGB]"
                else:
                    new_description = generated_description
                
                success = await self.homebox_service.update_location(selected_location.id, {
                    'description': new_description
                })
                
                if success:
                    result_text = t(bot_lang, 'locations.description_updated').format(
                        location_name=selected_location.name
                    )
                else:
                    result_text = t(bot_lang, 'locations.description_generation_failed').format(
                        location_name=selected_location.name,
                        error="Failed to update location"
                    )
                
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    result_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                
            except Exception as e:
                await self.handle_error(e, "confirm_description_update", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "reject_description_update", LocationStates.confirming_description_update)
        async def reject_description_update(callback: CallbackQuery, state: FSMContext):
            """Reject description update and return to location management"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    t(bot_lang, 'locations.description_generation_cancelled'),
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                
            except Exception as e:
                await self.handle_error(e, "reject_description_update", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "regenerate_description", LocationStates.confirming_description_update)
        async def regenerate_description(callback: CallbackQuery, state: FSMContext):
            """Regenerate description for the same location"""
            try:
                data = await state.get_data()
                selected_location = data['selected_location']
                
                # Trigger regeneration by calling the generation handler
                callback.data = f"generate_desc_{selected_location.id}"
                await generate_location_description(callback, state)
                
            except Exception as e:
                await self.handle_error(e, "regenerate_description", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "cancel_description_generation")
        async def cancel_description_generation(callback: CallbackQuery, state: FSMContext):
            """Cancel description generation process"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    t(bot_lang, 'locations.description_generation_cancelled'),
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                
            except Exception as e:
                await self.handle_error(e, "cancel_description_generation", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
    
    def create_locations_view_keyboard(self, bot_lang: str, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
        """Create keyboard for locations view with pagination"""
        builder = InlineKeyboardBuilder()
        
        # Navigation buttons
        if total_pages > 1:
            nav_buttons = []
            if current_page > 0:
                nav_buttons.append(InlineKeyboardButton(text=t(bot_lang, 'common.previous'), callback_data=f"locations_view_page_{current_page-1}"))
            if current_page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(text=t(bot_lang, 'common.next'), callback_data=f"locations_view_page_{current_page+1}"))
            
            if nav_buttons:
                builder.row(*nav_buttons)
        
        # Back button
        builder.row(InlineKeyboardButton(text=t(bot_lang, 'common.back'), callback_data="back_to_location_management"))
        
        return builder.as_markup()
        