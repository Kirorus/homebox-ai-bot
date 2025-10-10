"""
Photo handling logic
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.states import ItemStates
from .base_handler import BaseHandler
from models.item import Item, ItemAnalysis
from models.user import UserSettings
from models.location import LocationManager
from services.ai_service import AIService
from services.image_service import ImageService
from services.homebox_service import HomeBoxService
from utils.validators import InputValidator
from bot.keyboards import KeyboardManager
from i18n.i18n_manager import t

logger = logging.getLogger(__name__)


class PhotoHandler(BaseHandler):
    """Handles photo processing workflow"""
    
    def __init__(self, settings, database, homebox_service: HomeBoxService, ai_service: AIService, image_service: ImageService, bot):
        super().__init__(settings, database)
        self.homebox_service = homebox_service
        self.ai_service = ai_service
        self.image_service = image_service
        self.validator = InputValidator()
        self.bot = bot
        self.keyboard_manager = KeyboardManager()
        self.register_handlers()
    
    def register_handlers(self):
        """Register photo-related handlers"""
        
        @self.router.message(Command("start"))
        async def cmd_start(message: Message, state: FSMContext):
            """Handle /start command"""
            try:
                await self.log_user_action("start_command", message.from_user.id, {
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name
                })
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    user_settings = await self.get_user_settings(message.from_user.id)
                    bot_lang = user_settings.bot_lang
                    await message.answer(t(bot_lang, 'errors.access_denied'))
                    return
                
                await state.clear()
                
                # Get or create user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                if not user_settings:
                    # New user
                    user_settings = UserSettings(user_id=message.from_user.id)
                    await self.database.set_user_settings(message.from_user.id, user_settings.to_dict())
                    await self.log_user_action("first_time_user", message.from_user.id)
                
                # Update statistics
                await self.database.add_user(
                    message.from_user.id,
                    message.from_user.username,
                    message.from_user.first_name,
                    message.from_user.last_name
                )
                await self.database.increment_requests()
                
                bot_lang = user_settings.bot_lang
                start_message = self.create_beautiful_start_message(bot_lang)
                await message.answer(
                    start_message,
                    reply_markup=self.keyboard_manager.main_menu_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                await state.set_state(ItemStates.waiting_for_photo)
                
            except Exception as e:
                await self.handle_error(e, "start command handler", message.from_user.id)
                await message.answer("An error occurred. Please try again.")
        
        @self.router.message(ItemStates.waiting_for_photo, F.photo)
        async def handle_photo(message: Message, state: FSMContext):
            """Handle photo upload"""
            try:
                await self.log_user_action("photo_received", message.from_user.id, {
                    "caption": message.caption,
                    "photo_size": len(message.photo) if message.photo else 0
                })
                
                # Update statistics
                await self.database.increment_requests()
                
                if not await self.is_user_allowed(message.from_user.id):
                    user_settings = await self.get_user_settings(message.from_user.id)
                    bot_lang = user_settings.bot_lang
                    await message.answer(t(bot_lang, 'errors.access_denied'))
                    return
                
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Send initial loading indicator with progress
                progress_msg = await message.answer(
                    self.create_progress_message(bot_lang, 1, 5, t(bot_lang, 'processing.photo')),
                    parse_mode="Markdown"
                )
                
                # Get photo in maximum quality
                photo = message.photo[-1]
                
                # Download photo
                file = await self.bot.get_file(photo.file_id)
                file_path = f"../temp/temp_{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                await self.bot.download_file(file.file_path, file_path)
                
                # Update progress - AI analysis
                await progress_msg.edit_text(
                    self.create_progress_message(bot_lang, 2, 5, t(bot_lang, 'processing.analyzing')),
                    parse_mode="Markdown"
                )
                
                # Validate image
                is_valid, error_msg = self.image_service.validate_image(file_path)
                if not is_valid:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    await progress_msg.delete()
                    await message.answer(f"{t(bot_lang, 'errors.invalid_name')}: {error_msg}\n\n{t(bot_lang, 'errors.try_again')}")
                    return
                
                # Get locations from HomeBox
                locations = await self.homebox_service.get_locations()
                if not locations:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    await progress_msg.delete()
                    await message.answer(t(bot_lang, 'errors.occurred'))
                    await state.clear()
                    return
                
                # Create location manager
                location_manager = self.homebox_service.get_location_manager(locations)
                allowed_locations = location_manager.get_allowed_locations(
                    self.settings.homebox.location_filter_mode,
                    self.settings.homebox.location_marker
                )
                
                if not allowed_locations:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    await progress_msg.delete()
                    await message.answer(t(bot_lang, 'errors.no_locations'))
                    await state.clear()
                    return
                
                # Analyze image
                model = user_settings.model
                gen_lang = user_settings.gen_lang
                caption = message.caption if message.caption else None
                
                analysis = await self.ai_service.analyze_image(
                    file_path, location_manager, gen_lang, model, caption
                )
                
                # Update progress - Finding location
                await progress_msg.edit_text(
                    self.create_progress_message(bot_lang, 3, 5, t(bot_lang, 'processing.finding_location')),
                    parse_mode="Markdown"
                )
                
                # Find suggested location
                suggested_location = location_manager.find_best_match(analysis.suggested_location)
                if not suggested_location:
                    suggested_location = allowed_locations[0]
                
                # Create item
                item = Item(
                    name=analysis.name,
                    description=analysis.description,
                    location_id=suggested_location.id,
                    location_name=suggested_location.name,
                    photo_path=file_path,
                    photo_file_id=photo.file_id,
                    analysis=analysis
                )
                
                # Store item data in FSM
                await state.update_data(item=item, locations=allowed_locations)
                
                # Update progress - Item ready
                await progress_msg.edit_text(
                    self.create_progress_message(bot_lang, 4, 5, t(bot_lang, 'processing.creating')),
                    parse_mode="Markdown"
                )
                
                # Small delay for better UX
                await asyncio.sleep(0.5)
                
                # Remove progress message
                try:
                    await progress_msg.delete()
                except Exception:
                    pass
                
                # Send result
                result_caption = (
                    f"**{t(bot_lang, 'item.analysis_complete')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"✨ {t(bot_lang, 'item.what_change')}"
                )
                
                result_msg = await message.answer_photo(
                    photo=photo.file_id,
                    caption=result_caption,
                    reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                    parse_mode="Markdown"
                )

                # Remember the confirmation message to edit it later during edits
                try:
                    await state.update_data(confirm_message_id=result_msg.message_id, confirm_chat_id=result_msg.chat.id)
                except Exception:
                    pass

                await state.set_state(ItemStates.confirming_data)
                await self.log_user_action("photo_analyzed", message.from_user.id, {
                    "analysis_result": analysis.__dict__,
                    "model_used": model
                })
                
            except Exception as e:
                await self.handle_error(e, "photo handling", message.from_user.id)
                
                # Clean up temporary files on error
                temp_files = [f for f in os.listdir('../temp') if f.startswith(f'temp_{message.from_user.id}_')]
                for temp_file in temp_files:
                    try:
                        os.remove(f'../temp/{temp_file}')
                    except Exception:
                        pass
                
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                await message.answer(t(bot_lang, 'errors.photo_processing'))
        
        # Callback handlers for editing
        @self.router.callback_query(F.data == "edit_name", ItemStates.confirming_data)
        async def edit_name_callback(callback: CallbackQuery, state: FSMContext):
            """Handle edit name callback"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Remember the message id for further edits
                try:
                    await state.update_data(confirm_message_id=callback.message.message_id, confirm_chat_id=callback.message.chat.id)
                except Exception:
                    pass

                await callback.message.edit_caption(
                    caption=f"✏️ **{t(bot_lang, 'edit.name_title')}**\n\n{t(bot_lang, 'edit.name_prompt')}",
                    reply_markup=self.keyboard_manager.cancel_keyboard(bot_lang, "cancel_edit"),
                    parse_mode="Markdown"
                )
                await state.set_state(ItemStates.editing_name)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "edit_name_callback", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.callback_query(F.data == "edit_description", ItemStates.confirming_data)
        async def edit_description_callback(callback: CallbackQuery, state: FSMContext):
            """Handle edit description callback"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Remember the message id for further edits
                try:
                    await state.update_data(confirm_message_id=callback.message.message_id, confirm_chat_id=callback.message.chat.id)
                except Exception:
                    pass

                await callback.message.edit_caption(
                    caption=f"✏️ **{t(bot_lang, 'edit.description_title')}**\n\n{t(bot_lang, 'edit.description_prompt')}",
                    reply_markup=self.keyboard_manager.cancel_keyboard(bot_lang, "cancel_edit"),
                    parse_mode="Markdown"
                )
                await state.set_state(ItemStates.editing_description)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "edit_description_callback", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.callback_query(F.data == "edit_location", ItemStates.confirming_data)
        async def edit_location_callback(callback: CallbackQuery, state: FSMContext):
            """Handle edit location callback"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current data
                data = await state.get_data()
                locations = data.get('locations', [])
                
                if not locations:
                    await callback.answer("No locations available", show_alert=True)
                    return
                
                await callback.message.edit_caption(
                    caption=f"📦 **{t(bot_lang, 'edit.location_title')}**\n\n{t(bot_lang, 'edit.location_prompt')}",
                    reply_markup=self.keyboard_manager.locations_keyboard(locations, bot_lang),
                    parse_mode="Markdown"
                )
                await state.set_state(ItemStates.selecting_location)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "edit_location_callback", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.message(ItemStates.editing_name, F.text)
        async def handle_name_edit(message: Message, state: FSMContext):
            """Handle name editing"""
            try:
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Validate name
                is_valid, error_msg = self.validator.validate_item_name(message.text)
                if not is_valid:
                    await message.answer(f"❌ {t(bot_lang, 'error.invalid_name')}: {error_msg}\n\n{t(bot_lang, 'error.try_again')}")
                    return
                
                # Update item data
                data = await state.get_data()
                item = data.get('item')
                if item:
                    item.name = message.text.strip()
                    await state.update_data(item=item)
                
                # Show updated confirmation
                result_caption = (
                    f"**{t(bot_lang, 'item.analysis_complete')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"✨ {t(bot_lang, 'item.what_change')}"
                )
                
                # Try to edit previous confirmation message instead of sending a new one
                data = await state.get_data()
                confirm_message_id = data.get('confirm_message_id')
                confirm_chat_id = data.get('confirm_chat_id')
                edited_ok = False
                if confirm_message_id and confirm_chat_id:
                    try:
                        await self.bot.edit_message_caption(
                            chat_id=confirm_chat_id,
                            message_id=confirm_message_id,
                            caption=result_caption,
                            reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                            parse_mode="Markdown"
                        )
                        edited_ok = True
                    except Exception:
                        edited_ok = False

                if not edited_ok:
                    await message.answer_photo(
                        photo=item.photo_file_id,
                        caption=result_caption,
                        reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                        parse_mode="Markdown"
                    )
                
                await state.set_state(ItemStates.confirming_data)
                await self.log_user_action("name_edited", message.from_user.id, {"new_name": message.text})
                
            except Exception as e:
                await self.handle_error(e, "name_editing", message.from_user.id)
                await message.answer("An error occurred. Please try again.")

        @self.router.callback_query(F.data == "cancel_edit", StateFilter(ItemStates.editing_name, ItemStates.editing_description))
        async def cancel_edit_callback(callback: CallbackQuery, state: FSMContext):
            """Cancel edit (name/description) and delete the prompt message"""
            try:
                # Do not delete temp file here; still in editing, just close prompt
                await state.set_state(ItemStates.confirming_data)
                try:
                    await callback.message.delete()
                except Exception:
                    try:
                        await callback.message.edit_caption(caption=" ", reply_markup=None)
                    except Exception:
                        pass
                await callback.answer()
            except Exception as e:
                await self.handle_error(e, "cancel_edit", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.message(ItemStates.editing_description, F.text)
        async def handle_description_edit(message: Message, state: FSMContext):
            """Handle description editing"""
            try:
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Validate description
                is_valid, error_msg = self.validator.validate_item_description(message.text)
                if not is_valid:
                    await message.answer(f"❌ Invalid description: {error_msg}\n\nPlease try again:")
                    return
                
                # Update item data
                data = await state.get_data()
                item = data.get('item')
                if item:
                    item.description = message.text.strip()
                    await state.update_data(item=item)
                
                # Show updated confirmation
                result_caption = (
                    f"**{t(bot_lang, 'item.analysis_complete')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"✨ {t(bot_lang, 'item.what_change')}"
                )
                
                # Try to edit previous confirmation message instead of sending a new one
                data = await state.get_data()
                confirm_message_id = data.get('confirm_message_id')
                confirm_chat_id = data.get('confirm_chat_id')
                edited_ok = False
                if confirm_message_id and confirm_chat_id:
                    try:
                        await self.bot.edit_message_caption(
                            chat_id=confirm_chat_id,
                            message_id=confirm_message_id,
                            caption=result_caption,
                            reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                            parse_mode="Markdown"
                        )
                        edited_ok = True
                    except Exception:
                        edited_ok = False

                if not edited_ok:
                    await message.answer_photo(
                        photo=item.photo_file_id,
                        caption=result_caption,
                        reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                        parse_mode="Markdown"
                    )
                
                await state.set_state(ItemStates.confirming_data)
                await self.log_user_action("description_edited", message.from_user.id, {"new_description": message.text})
                
            except Exception as e:
                await self.handle_error(e, "description_editing", message.from_user.id)
                await message.answer("An error occurred. Please try again.")
        
        @self.router.callback_query(F.data.startswith("location_"), ItemStates.selecting_location)
        async def handle_location_selection(callback: CallbackQuery, state: FSMContext):
            """Handle location selection"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Extract location ID from callback data
                location_id = callback.data.split("_", 1)[1]
                
                # Get current data
                data = await state.get_data()
                item = data.get('item')
                locations = data.get('locations', [])
                
                if not item or not locations:
                    await callback.answer("Error: No item data found", show_alert=True)
                    return
                
                # Find selected location
                selected_location = None
                for loc in locations:
                    if loc.id == location_id:
                        selected_location = loc
                        break
                
                if not selected_location:
                    await callback.answer("Location not found", show_alert=True)
                    return
                
                # Update item data
                item.location_id = selected_location.id
                item.location_name = selected_location.name
                await state.update_data(item=item)
                
                # Show updated confirmation
                result_caption = (
                    f"**{t(bot_lang, 'item.analysis_complete')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"✨ {t(bot_lang, 'item.what_change')}"
                )
                
                await callback.message.edit_caption(
                    caption=result_caption,
                    reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                
                await state.set_state(ItemStates.confirming_data)
                await callback.answer()
                await self.log_user_action("location_edited", callback.from_user.id, {"new_location": selected_location.name})
                
            except Exception as e:
                await self.handle_error(e, "location_selection", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)

        @self.router.callback_query(F.data == "cancel_location", ItemStates.selecting_location)
        async def cancel_location_callback(callback: CallbackQuery, state: FSMContext):
            """Cancel location selection and delete the message"""
            try:
                await state.set_state(ItemStates.confirming_data)
                try:
                    await callback.message.delete()
                except Exception:
                    try:
                        await callback.message.edit_caption(caption=" ", reply_markup=None)
                    except Exception:
                        pass
                await callback.answer()
            except Exception as e:
                await self.handle_error(e, "cancel_location", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.callback_query(F.data == "back_to_confirm", ItemStates.selecting_location)
        async def back_to_confirm_callback(callback: CallbackQuery, state: FSMContext):
            """Handle back to confirmation"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current data
                data = await state.get_data()
                item = data.get('item')
                
                if not item:
                    await callback.answer("Error: No item data found", show_alert=True)
                    return
                
                # Show confirmation again
                result_caption = (
                    f"**{t(bot_lang, 'item.analysis_complete')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"✨ {t(bot_lang, 'item.what_change')}"
                )
                
                await callback.message.edit_caption(
                    caption=result_caption,
                    reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                
                await state.set_state(ItemStates.confirming_data)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "back_to_confirm", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.callback_query(F.data == "confirm", ItemStates.confirming_data)
        async def confirm_item_callback(callback: CallbackQuery, state: FSMContext):
            """Handle item confirmation and creation"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get item data
                data = await state.get_data()
                item = data.get('item')
                
                if not item:
                    await callback.answer("Error: No item data found", show_alert=True)
                    return
                
                # Show processing message with progress
                await callback.message.edit_caption(
                    caption=self.create_progress_message(bot_lang, 4, 5, t(bot_lang, 'processing.creating')),
                    reply_markup=None,
                    parse_mode="Markdown"
                )
                
                # Update progress - Uploading photo
                await callback.message.edit_caption(
                    caption=self.create_progress_message(bot_lang, 5, 5, t(bot_lang, 'processing.uploading_photo')),
                    reply_markup=None,
                    parse_mode="Markdown"
                )
                
                # Create item in HomeBox
                result = await self.homebox_service.create_item(item)
                
                if 'error' in result:
                    await callback.message.edit_caption(
                        caption=f"❌ **{t(bot_lang, 'item.error_creating')}**\n\n{result['error']}\n\n{t(bot_lang, 'error.try_again')}",
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                    await callback.answer("Failed to create item", show_alert=True)
                    return
                
                # Success message
                success_caption = (
                    f"✅ **{t(bot_lang, 'item.success')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"🎉 {t(bot_lang, 'item.success_desc')}"
                )
                
                await callback.message.edit_caption(
                    caption=success_caption,
                    reply_markup=None,
                    parse_mode="Markdown"
                )
                
                # Clean up temporary files
                if item.photo_path and os.path.exists(item.photo_path):
                    try:
                        os.remove(item.photo_path)
                    except Exception:
                        pass
                
                # Update statistics
                await self.database.increment_items_processed()
                
                # Clear state
                await state.clear()
                await callback.answer("Item created successfully!")
                
                await self.log_user_action("item_created", callback.from_user.id, {
                    "item_name": item.name,
                    "location": item.location_name,
                    "homebox_id": result.get('id')
                })
                
            except Exception as e:
                await self.handle_error(e, "confirm_item", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.callback_query(F.data == "reanalyze", ItemStates.confirming_data)
        async def reanalyze_callback(callback: CallbackQuery, state: FSMContext):
            """Handle re-analysis request"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                await callback.message.edit_caption(
                    caption=f"🔄 **{t(bot_lang, 'reanalysis.title')}**\n\n{t(bot_lang, 'reanalysis.prompt')}\n\n💡 *{t(bot_lang, 'reanalysis.hint_placeholder')}*",
                    reply_markup=self.keyboard_manager.cancel_keyboard(bot_lang, "cancel_reanalysis"),
                    parse_mode="Markdown"
                )
                await state.set_state(ItemStates.waiting_for_reanalysis_hint)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "reanalyze_callback", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.message(ItemStates.waiting_for_reanalysis_hint, F.text)
        async def handle_reanalysis_hint(message: Message, state: FSMContext):
            """Handle re-analysis hint text"""
            try:
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current data
                data = await state.get_data()
                item = data.get('item')
                locations = data.get('locations', [])
                
                if not item or not locations:
                    await message.answer("Error: No item data found", show_alert=True)
                    return
                
                # Show processing message
                progress_msg = await message.answer(
                    f"🔄 **{t(bot_lang, 'reanalysis.processing')}**",
                    parse_mode="Markdown"
                )
                
                # Create location manager
                location_manager = self.homebox_service.get_location_manager(locations)
                
                # Re-analyze with hint
                model = user_settings.model
                gen_lang = user_settings.gen_lang
                hint = message.text.strip()
                
                analysis = await self.ai_service.analyze_image(
                    item.photo_path, location_manager, gen_lang, model, hint
                )
                
                # Find suggested location
                suggested_location = location_manager.find_best_match(analysis.suggested_location)
                if not suggested_location:
                    suggested_location = locations[0]
                
                # Update item with new analysis
                item.name = analysis.name
                item.description = analysis.description
                item.location_id = suggested_location.id
                item.location_name = suggested_location.name
                item.analysis = analysis
                
                await state.update_data(item=item)
                
                # Remove progress message
                try:
                    await progress_msg.delete()
                except Exception:
                    pass
                
                # Show updated result
                result_caption = (
                    f"**{t(bot_lang, 'item.analysis_complete')}**\n\n"
                    f"📝 **{t(bot_lang, 'item.name')}:** `{item.name}`\n"
                    f"📋 **{t(bot_lang, 'item.description')}:** `{item.description}`\n"
                    f"📦 **{t(bot_lang, 'item.location')}:** `{item.location_name}`\n\n"
                    f"✨ {t(bot_lang, 'item.what_change')}"
                )
                
                await message.answer_photo(
                    photo=item.photo_file_id,
                    caption=result_caption,
                    reply_markup=self.keyboard_manager.confirmation_keyboard(bot_lang),
                    parse_mode="Markdown"
                )
                
                await state.set_state(ItemStates.confirming_data)
                await self.log_user_action("item_reanalyzed", message.from_user.id, {
                    "hint": hint,
                    "new_analysis": analysis.__dict__,
                    "model_used": model
                })
                
            except Exception as e:
                await self.handle_error(e, "reanalysis_hint", message.from_user.id)
                await message.answer("An error occurred during re-analysis. Please try again.")

        @self.router.callback_query(F.data == "cancel_reanalysis", ItemStates.waiting_for_reanalysis_hint)
        async def cancel_reanalysis_callback(callback: CallbackQuery, state: FSMContext):
            """Cancel reanalysis input and delete the prompt message"""
            try:
                await state.set_state(ItemStates.confirming_data)
                try:
                    await callback.message.delete()
                except Exception:
                    try:
                        await callback.message.edit_caption(caption=" ", reply_markup=None)
                    except Exception:
                        pass
                await callback.answer()
            except Exception as e:
                await self.handle_error(e, "cancel_reanalysis", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
        
        @self.router.callback_query(F.data == "cancel", ItemStates.confirming_data)
        async def cancel_item_callback(callback: CallbackQuery, state: FSMContext):
            """Handle item cancellation"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get item data for cleanup
                data = await state.get_data()
                item = data.get('item')
                
                # Clean up temporary files
                if item and item.photo_path and os.path.exists(item.photo_path):
                    try:
                        os.remove(item.photo_path)
                    except Exception:
                        pass
                
                # Clear state
                await state.clear()

                # Delete the confirmation message entirely for cleaner UX
                try:
                    await callback.message.delete()
                except Exception:
                    # Fallback: remove keyboard and clear caption silently
                    try:
                        await callback.message.edit_caption(caption=" ", reply_markup=None)
                    except Exception:
                        pass

                # Answer callback without alert
                await callback.answer()
                await self.log_user_action("item_cancelled", callback.from_user.id)
                
            except Exception as e:
                await self.handle_error(e, "cancel_item", callback.from_user.id)
                await callback.answer("Error occurred", show_alert=True)
