"""
Search handling logic
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from .base_handler import BaseHandler
from bot.states import SearchStates, LocationStates
from bot.keyboards import KeyboardManager
from i18n.i18n_manager import t

logger = logging.getLogger(__name__)


class SearchHandler(BaseHandler):
    """Handles search-related commands"""
    
    def __init__(self, settings, database, homebox_service, ai_service, image_service):
        super().__init__(settings, database)
        self.homebox_service = homebox_service
        self.ai_service = ai_service
        self.image_service = image_service
        self.keyboard_manager = KeyboardManager()
        self.register_handlers()
    
    def register_handlers(self):
        """Register search-related handlers"""
        
        @self.router.message(Command("search"))
        async def cmd_search(message: Message, state: FSMContext):
            """Handle /search command"""
            try:
                await self.log_user_action("search_command", message.from_user.id)
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    await message.answer(t('en', 'errors.access_denied'))
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                search_text = t(bot_lang, 'search.enter_query')
                await message.answer(
                    search_text,
                    reply_markup=self.keyboard_manager.search_cancel_keyboard(bot_lang)
                )
                await state.set_state(SearchStates.waiting_for_search_query)
                
            except Exception as e:
                await self.handle_error(e, "search command", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.message(SearchStates.waiting_for_search_query)
        async def handle_search_query(message: Message, state: FSMContext):
            """Handle search query input"""
            try:
                await self.log_user_action("search_query", message.from_user.id, {"query": message.text})
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    await message.answer(t('en', 'errors.access_denied'))
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                query = message.text.strip()
                if not query:
                    await message.answer(t(bot_lang, 'search.empty_query'))
                    return
                
                # Show searching message
                searching_msg = await message.answer(t(bot_lang, 'search.searching'))
                
                # Search items
                logger.info(f"Searching for query: '{query}'")
                items = await self.homebox_service.search_items(query, limit=20)
                logger.info(f"Search returned {len(items) if items else 0} items")
                
                if not items:
                    try:
                        await searching_msg.edit_text(t(bot_lang, 'search.no_results'))
                    except:
                        await message.answer(t(bot_lang, 'search.no_results'))
                    await state.clear()
                    return
                
                # Store search results in state
                await state.update_data(search_results=items, current_page=0)
                
                # Show search results
                try:
                    await self.show_search_results(message, state, items, 0, bot_lang)
                    await state.set_state(SearchStates.viewing_search_results)
                except Exception as e:
                    # If editing fails, send a new message
                    await self.handle_error(e, "search query", message.from_user.id)
                    await message.answer(
                        t(bot_lang, 'search.no_results'),
                        reply_markup=self.keyboard_manager.search_cancel_keyboard(bot_lang)
                    )
                    await state.clear()
                
            except Exception as e:
                await self.handle_error(e, "search query", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        
        @self.router.message(Command("recent"))
        async def cmd_recent(message: Message, state: FSMContext):
            """Handle /recent command - show recent items"""
            try:
                await self.log_user_action("recent_command", message.from_user.id)
                
                # Check user authorization
                if not await self.is_user_allowed(message.from_user.id):
                    await message.answer(t('en', 'errors.access_denied'))
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Show loading message
                loading_msg = await message.answer(t(bot_lang, 'search.loading_recent'))
                
                # Get recent items (first page)
                items = await self.homebox_service.get_items(limit=20, offset=0)
                
                if not items:
                    await loading_msg.edit_text(t(bot_lang, 'search.no_items'))
                    return
                
                # Store results in state
                await state.update_data(search_results=items, current_page=0)
                
                # Show recent items
                await self.show_search_results(message, state, items, 0, bot_lang, is_recent=True)
                await state.set_state(SearchStates.viewing_search_results)
                
            except Exception as e:
                await self.handle_error(e, "recent command", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data.startswith("search_item_"))
        async def view_item_details(callback: CallbackQuery, state: FSMContext):
            """View detailed information about a specific item"""
            try:
                # Extract item ID from callback data
                item_id = callback.data.split("_", 2)[2]
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get item details
                item = await self.homebox_service.get_item_by_id(item_id)
                
                if not item:
                    await callback.answer(t(bot_lang, 'search.item_not_found'), show_alert=True)
                    return
                
                # Show item details
                details_text = self.format_item_details(item, bot_lang)
                image_url = await self.get_item_image_url(item)
                
                # Log image URL for debugging
                logger.info(f"Item {item_id} image URL: {image_url}")
                
                # Try to send photo with caption, fallback to text only
                if image_url:
                    try:
                        await callback.message.delete()
                        await callback.message.answer_photo(
                            photo=image_url,
                            caption=details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    except Exception as photo_error:
                        logger.warning(f"Failed to send photo for item {item_id}: {photo_error}")
                        # Fallback to text message
                        await callback.message.answer(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                else:
                    # No image, send text only
                    try:
                        await callback.message.edit_text(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await callback.message.answer(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                
                await callback.answer()
                await state.set_state(SearchStates.viewing_item_details)
                
            except Exception as e:
                await self.handle_error(e, "view_item_details", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "search_back")
        async def back_to_search_results(callback: CallbackQuery, state: FSMContext):
            """Return to search results"""
            try:
                data = await state.get_data()
                search_results = data.get('search_results', [])
                current_page = data.get('current_page', 0)
                
                if not search_results:
                    await callback.answer(t('en', 'search.no_results'), show_alert=True)
                    return
                
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                await self.show_search_results(
                    callback.message, state, search_results, current_page, bot_lang
                )
                await callback.answer()
                await state.set_state(SearchStates.viewing_search_results)
                
            except Exception as e:
                await self.handle_error(e, "back_to_search_results", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("search_page_"))
        async def change_search_page(callback: CallbackQuery, state: FSMContext):
            """Change search results page"""
            try:
                # Extract page number from callback data
                page = int(callback.data.split("_")[-1])
                
                data = await state.get_data()
                search_results = data.get('search_results', [])
                
                if not search_results:
                    await callback.answer(t('en', 'search.no_results'), show_alert=True)
                    return
                
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Calculate page size
                page_size = 5
                total_pages = (len(search_results) + page_size - 1) // page_size
                
                if page < 0 or page >= total_pages:
                    await callback.answer(t(bot_lang, 'search.invalid_page'), show_alert=True)
                    return
                
                # Update current page
                await state.update_data(current_page=page)
                
                await self.show_search_results(
                    callback.message, state, search_results, page, bot_lang
                )
                await callback.answer()
                
            except ValueError as e:
                logger.error(f"Invalid page number in search_page callback: {callback.data}")
                await callback.answer(t('en', 'search.invalid_page'), show_alert=True)
            except Exception as e:
                await self.handle_error(e, "change_search_page", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "search_cancel")
        async def cancel_search(callback: CallbackQuery, state: FSMContext):
            """Cancel search operation"""
            try:
                await state.clear()
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                try:
                    await callback.message.edit_text(t(bot_lang, 'search.cancelled'))
                except:
                    await callback.message.answer(t(bot_lang, 'search.cancelled'))
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "cancel_search", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "search_new")
        async def new_search(callback: CallbackQuery, state: FSMContext):
            """Start new search"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                search_text = t(bot_lang, 'search.enter_query')
                try:
                    await callback.message.edit_text(
                        search_text,
                        reply_markup=self.keyboard_manager.search_cancel_keyboard(bot_lang)
                    )
                except Exception as edit_error:
                    await callback.message.answer(
                        search_text,
                        reply_markup=self.keyboard_manager.search_cancel_keyboard(bot_lang)
                    )
                await callback.answer()
                await state.set_state(SearchStates.waiting_for_search_query)
                
            except Exception as e:
                await self.handle_error(e, "new_search", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("move_item_"))
        async def start_move_item(callback: CallbackQuery, state: FSMContext):
            """Start moving item to new location"""
            try:
                # Extract item ID from callback data
                item_id = callback.data.split("_", 2)[2]
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current item to show current location
                item = await self.homebox_service.get_item_by_id(item_id)
                if not item:
                    await callback.answer(t(bot_lang, 'search.item_not_found'), show_alert=True)
                    return
                
                # Get all locations
                all_locations = await self.homebox_service.get_locations()
                if not all_locations:
                    await callback.answer(t(bot_lang, 'errors.no_locations'), show_alert=True)
                    return
                
                # Filter locations using the same logic as item creation
                location_manager = self.homebox_service.get_location_manager(all_locations)
                allowed_locations = location_manager.get_allowed_locations(
                    self.settings.homebox.location_filter_mode,
                    self.settings.homebox.location_marker
                )
                
                if not allowed_locations:
                    await callback.answer(t(bot_lang, 'errors.no_locations'), show_alert=True)
                    return
                
                # Get current location ID
                current_location_id = item.get('location', {}).get('id', '') if isinstance(item.get('location'), dict) else ''
                
                # Show location selection
                move_text = t(bot_lang, 'search.select_new_location').format(
                    item_name=item.get('name', 'Unknown Item'),
                    current_location=item.get('location', {}).get('name', 'Unknown Location') if isinstance(item.get('location'), dict) else 'Unknown Location'
                )
                
                try:
                    await callback.message.edit_text(
                        move_text,
                        reply_markup=self.keyboard_manager.move_item_location_keyboard(
                            allowed_locations, current_location_id, bot_lang, item_id
                        ),
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    await callback.message.answer(
                        move_text,
                        reply_markup=self.keyboard_manager.move_item_location_keyboard(
                            allowed_locations, current_location_id, bot_lang, item_id
                        ),
                        parse_mode="Markdown"
                    )
                
                # Create location mapping for callback data
                location_mapping = {}
                filtered_locations = []
                for loc in allowed_locations:
                    if str(loc.id) != str(current_location_id):
                        location_mapping[len(filtered_locations)] = loc.id
                        filtered_locations.append(loc)
                
                await callback.answer()
                await state.set_state(SearchStates.selecting_new_location)
                await state.update_data(
                    moving_item_id=item_id, 
                    current_item=item,
                    location_mapping=location_mapping,
                    filtered_locations=filtered_locations
                )
                
            except Exception as e:
                await self.handle_error(e, "start_move_item", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("mov_loc_"))
        async def confirm_move_item(callback: CallbackQuery, state: FSMContext):
            """Move item to selected location"""
            try:
                # Extract location index from callback data
                location_index = int(callback.data.split("_")[2])
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get state data
                data = await state.get_data()
                current_item = data.get('current_item', {})
                item_id = data.get('moving_item_id', '')
                location_mapping = data.get('location_mapping', {})
                
                # Get location ID from mapping
                if location_index not in location_mapping:
                    await callback.answer(t(bot_lang, 'errors.location_not_found'), show_alert=True)
                    return
                
                new_location_id = location_mapping[location_index]
                
                # Show moving message
                moving_msg = await callback.message.answer(t(bot_lang, 'search.moving_item'))
                
                # Update item location
                success = await self.homebox_service.update_item_location(item_id, new_location_id)
                
                if success:
                    # Get updated item and new location info
                    updated_item = await self.homebox_service.get_item_by_id(item_id)
                    all_locations = await self.homebox_service.get_locations()
                    new_location_name = "Unknown Location"
                    
                    if all_locations:
                        for loc in all_locations:
                            if str(loc.id) == str(new_location_id):
                                new_location_name = loc.name
                                break
                    
                    # Show success message
                    success_text = t(bot_lang, 'search.item_moved_successfully').format(
                        item_name=current_item.get('name', 'Unknown Item'),
                        new_location=new_location_name
                    )
                    
                    try:
                        await moving_msg.edit_text(
                            success_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await callback.message.answer(
                            success_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    
                    await state.set_state(SearchStates.viewing_item_details)
                    await state.update_data(current_item=updated_item)
                    
                else:
                    # Show error message
                    error_text = t(bot_lang, 'search.move_failed').format(
                        error=self.homebox_service.last_error or 'Unknown error'
                    )
                    
                    try:
                        await moving_msg.edit_text(
                            error_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await callback.message.answer(
                            error_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "confirm_move_item", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data == "mov_back")
        async def back_to_item_details(callback: CallbackQuery, state: FSMContext):
            """Return to item details from location selection"""
            try:
                # Get state data
                data = await state.get_data()
                item_id = data.get('moving_item_id', '')
                
                if not item_id:
                    await callback.answer(t('en', 'search.item_not_found'), show_alert=True)
                    return
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get updated item details
                item = await self.homebox_service.get_item_by_id(item_id)
                if not item:
                    await callback.answer(t(bot_lang, 'search.item_not_found'), show_alert=True)
                    return
                
                # Show item details
                details_text = self.format_item_details(item, bot_lang)
                image_url = await self.get_item_image_url(item)
                
                # Try to send photo with caption, fallback to text only
                if image_url:
                    try:
                        await callback.message.edit_text(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await callback.message.answer(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                else:
                    # No image, send text only
                    try:
                        await callback.message.edit_text(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await callback.message.answer(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                            parse_mode="Markdown"
                        )
                
                await callback.answer()
                await state.set_state(SearchStates.viewing_item_details)
                await state.update_data(current_item=item)
                
            except Exception as e:
                await self.handle_error(e, "back_to_item_details", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("edit_item_name_"))
        async def start_edit_item_name(callback: CallbackQuery, state: FSMContext):
            """Start editing item name"""
            try:
                # Extract item ID from callback data
                item_id = callback.data.split("_", 3)[3]
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current item
                item = await self.homebox_service.get_item_by_id(item_id)
                if not item:
                    await callback.answer(t(bot_lang, 'search.item_not_found'), show_alert=True)
                    return
                
                # Show edit prompt
                edit_text = f"✏️ **{t(bot_lang, 'edit.name_title')}**\n\n{t(bot_lang, 'edit.name_prompt')}"
                
                try:
                    await callback.message.edit_text(
                        edit_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    await callback.message.answer(
                        edit_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                
                await callback.answer()
                await state.set_state(SearchStates.editing_item_name)
                await state.update_data(editing_item_id=item_id, current_item=item)
                
            except Exception as e:
                await self.handle_error(e, "start_edit_item_name", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("edit_item_desc_"))
        async def start_edit_item_description(callback: CallbackQuery, state: FSMContext):
            """Start editing item description"""
            try:
                # Extract item ID from callback data
                item_id = callback.data.split("_", 3)[3]
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current item
                item = await self.homebox_service.get_item_by_id(item_id)
                if not item:
                    await callback.answer(t(bot_lang, 'search.item_not_found'), show_alert=True)
                    return
                
                # Show edit prompt
                edit_text = f"✏️ **{t(bot_lang, 'edit.description_title')}**\n\n{t(bot_lang, 'edit.description_prompt')}"
                
                try:
                    await callback.message.edit_text(
                        edit_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    await callback.message.answer(
                        edit_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                
                await callback.answer()
                await state.set_state(SearchStates.editing_item_description)
                await state.update_data(editing_item_id=item_id, current_item=item)
                
            except Exception as e:
                await self.handle_error(e, "start_edit_item_description", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.callback_query(F.data.startswith("reanalyze_item_"))
        async def start_reanalyze_item(callback: CallbackQuery, state: FSMContext):
            """Start reanalyzing item"""
            try:
                # Extract item ID from callback data
                item_id = callback.data.split("_", 2)[2]
                
                # Get user settings
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get current item
                item = await self.homebox_service.get_item_by_id(item_id)
                if not item:
                    await callback.answer(t(bot_lang, 'search.item_not_found'), show_alert=True)
                    return
                
                # Show reanalysis prompt
                reanalyze_text = f"🔄 **{t(bot_lang, 'reanalysis.title')}**\n\n{t(bot_lang, 'reanalysis.prompt')}\n\n💡 *{t(bot_lang, 'reanalysis.hint_placeholder')}*"
                
                try:
                    await callback.message.edit_text(
                        reanalyze_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    await callback.message.answer(
                        reanalyze_text,
                        reply_markup=None,
                        parse_mode="Markdown"
                    )
                
                await callback.answer()
                await state.set_state(SearchStates.waiting_for_reanalysis_hint)
                await state.update_data(reanalyzing_item_id=item_id, current_item=item)
                
            except Exception as e:
                await self.handle_error(e, "start_reanalyze_item", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'), show_alert=True)
        
        @self.router.message(SearchStates.editing_item_name, F.text)
        async def handle_item_name_edit(message: Message, state: FSMContext):
            """Handle item name editing"""
            try:
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get state data
                data = await state.get_data()
                item_id = data.get('editing_item_id', '')
                
                if not item_id:
                    await message.answer(t(bot_lang, 'search.item_not_found'))
                    return
                
                # Validate name (basic validation)
                new_name = message.text.strip()
                if not new_name or len(new_name) < 1 or len(new_name) > 200:
                    await message.answer(t(bot_lang, 'errors.invalid_name'))
                    return
                
                # Show updating message
                updating_msg = await message.answer(t(bot_lang, 'search.updating_item'))
                
                # Update item in HomeBox
                success = await self.homebox_service.update_item(item_id, {'name': new_name})
                
                if success:
                    # Get updated item
                    updated_item = await self.homebox_service.get_item_by_id(item_id)
                    if updated_item:
                        # Show updated item details
                        details_text = self.format_item_details(updated_item, bot_lang)
                        image_url = await self.get_item_image_url(updated_item)
                        
                        success_text = t(bot_lang, 'search.item_updated_successfully').format(
                            field=t(bot_lang, 'edit.name_title'),
                            value=new_name
                        )
                        
                        try:
                            await updating_msg.edit_text(
                                success_text,
                                reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                                parse_mode="Markdown"
                            )
                        except Exception as edit_error:
                            await message.answer(
                                success_text,
                                reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                                parse_mode="Markdown"
                            )
                        
                        await state.set_state(SearchStates.viewing_item_details)
                        await state.update_data(current_item=updated_item)
                    else:
                        await updating_msg.edit_text(t(bot_lang, 'search.item_not_found'))
                else:
                    error_text = t(bot_lang, 'search.update_failed').format(
                        error=self.homebox_service.last_error or 'Unknown error'
                    )
                    await updating_msg.edit_text(error_text)
                
            except Exception as e:
                await self.handle_error(e, "handle_item_name_edit", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.message(SearchStates.editing_item_description, F.text)
        async def handle_item_description_edit(message: Message, state: FSMContext):
            """Handle item description editing"""
            try:
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                
                # Get state data
                data = await state.get_data()
                item_id = data.get('editing_item_id', '')
                
                if not item_id:
                    await message.answer(t(bot_lang, 'search.item_not_found'))
                    return
                
                # Validate description (basic validation)
                new_description = message.text.strip()
                if len(new_description) > 1000:
                    await message.answer(t(bot_lang, 'errors.invalid_description'))
                    return
                
                # Show updating message
                updating_msg = await message.answer(t(bot_lang, 'search.updating_item'))
                
                # Update item in HomeBox
                success = await self.homebox_service.update_item(item_id, {'description': new_description})
                
                if success:
                    # Get updated item
                    updated_item = await self.homebox_service.get_item_by_id(item_id)
                    if updated_item:
                        success_text = t(bot_lang, 'search.item_updated_successfully').format(
                            field=t(bot_lang, 'edit.description_title'),
                            value=new_description[:50] + "..." if len(new_description) > 50 else new_description
                        )
                        
                        try:
                            await updating_msg.edit_text(
                                success_text,
                                reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                                parse_mode="Markdown"
                            )
                        except Exception as edit_error:
                            await message.answer(
                                success_text,
                                reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                                parse_mode="Markdown"
                            )
                        
                        await state.set_state(SearchStates.viewing_item_details)
                        await state.update_data(current_item=updated_item)
                    else:
                        await updating_msg.edit_text(t(bot_lang, 'search.item_not_found'))
                else:
                    error_text = t(bot_lang, 'search.update_failed').format(
                        error=self.homebox_service.last_error or 'Unknown error'
                    )
                    await updating_msg.edit_text(error_text)
                
            except Exception as e:
                await self.handle_error(e, "handle_item_description_edit", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
        
        @self.router.message(SearchStates.waiting_for_reanalysis_hint, F.text)
        async def handle_item_reanalysis_hint(message: Message, state: FSMContext):
            """Handle item reanalysis hint"""
            try:
                user_settings = await self.get_user_settings(message.from_user.id)
                bot_lang = user_settings.bot_lang
                gen_lang = user_settings.gen_lang
                
                # Get state data
                data = await state.get_data()
                item_id = data.get('reanalyzing_item_id', '')
                current_item = data.get('current_item', {})
                
                if not item_id or not current_item:
                    await message.answer(t(bot_lang, 'search.item_not_found'))
                    return
                
                hint = message.text.strip()
                
                # Show processing message
                processing_msg = await message.answer(t(bot_lang, 'reanalysis.processing'))
                
                # Get all locations for reanalysis
                all_locations = await self.homebox_service.get_locations()
                if not all_locations:
                    await processing_msg.edit_text(t(bot_lang, 'errors.no_locations'))
                    return
                
                # Filter locations
                location_manager = self.homebox_service.get_location_manager(all_locations)
                allowed_locations = location_manager.get_allowed_locations(
                    self.settings.homebox.location_filter_mode,
                    self.settings.homebox.location_marker
                )
                
                # Check if item has an image
                image_id = current_item.get('imageId', '')
                if not image_id:
                    await processing_msg.edit_text(t(bot_lang, 'search.no_image_for_reanalysis'))
                    return
                
                # Download item image for reanalysis
                image_path = await self.homebox_service.download_item_image(item_id, image_id)
                if not image_path:
                    await processing_msg.edit_text(t(bot_lang, 'search.image_download_failed'))
                    return
                
                try:
                    # Perform AI reanalysis with hint
                    analysis = await self.ai_service.analyze_image(
                        image_path=image_path,
                        location_manager=location_manager,
                        lang=gen_lang,
                        model=user_settings.model,
                        caption=hint  # Use hint as additional caption
                    )
                    
                    # Find the suggested location
                    suggested_location = None
                    for loc in allowed_locations:
                        if loc.name == analysis.suggested_location:
                            suggested_location = loc
                            break
                    
                    if not suggested_location:
                        suggested_location = allowed_locations[0] if allowed_locations else None
                    
                    if not suggested_location:
                        await processing_msg.edit_text(t(bot_lang, 'errors.no_locations'))
                        return
                    
                    # Update item with new analysis
                    update_data = {
                        'name': analysis.name,
                        'description': analysis.description,
                        'location_id': suggested_location.id
                    }
                    
                    success = await self.homebox_service.update_item(item_id, update_data)
                    
                    if success:
                        # Get updated item
                        updated_item = await self.homebox_service.get_item_by_id(item_id)
                        if updated_item:
                            success_text = t(bot_lang, 'search.reanalysis_successful').format(
                                hint=hint,
                                new_name=analysis.name,
                                new_description=analysis.description,
                                new_location=suggested_location.name
                            )
                            
                            try:
                                await processing_msg.edit_text(
                                    success_text,
                                    reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                                    parse_mode="Markdown"
                                )
                            except Exception as edit_error:
                                await message.answer(
                                    success_text,
                                    reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang, item_id),
                                    parse_mode="Markdown"
                                )
                            
                            await state.set_state(SearchStates.viewing_item_details)
                            await state.update_data(current_item=updated_item)
                        else:
                            await processing_msg.edit_text(t(bot_lang, 'search.item_not_found'))
                    else:
                        error_text = t(bot_lang, 'search.update_failed').format(
                            error=self.homebox_service.last_error or 'Unknown error'
                        )
                        await processing_msg.edit_text(error_text)
                
                finally:
                    # Clean up temporary image file
                    try:
                        import os
                        if image_path and os.path.exists(image_path):
                            os.remove(image_path)
                            logger.info(f"Cleaned up temporary image: {image_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temporary image {image_path}: {cleanup_error}")
                
            except Exception as e:
                await self.handle_error(e, "handle_item_reanalysis_hint", message.from_user.id)
                await message.answer(t('en', 'errors.occurred'))
    
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
        
        # Location management handlers
        @self.router.callback_query(F.data == "location_management")
        async def show_location_management(callback: CallbackQuery, state: FSMContext):
            """Show location management menu"""
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
                
            except Exception as e:
                await self.handle_error(e, "show_location_management", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
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
                current_page = data.get('current_page', 0)
                
                if location_id in selected_locations:
                    selected_locations.remove(location_id)
                else:
                    selected_locations.add(location_id)
                
                await state.update_data(selected_locations=selected_locations)
                
                # Update keyboard to reflect new selection
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
                selected_locations = data.get('selected_locations', set())
                
                await state.update_data(current_page=page)
                
                keyboard = self.keyboard_manager.locations_selection_keyboard(all_locations, bot_lang, page, selected_locations=selected_locations)
                
                await callback.message.edit_reply_markup(reply_markup=keyboard)
                await callback.answer()
                
            except Exception as e:
                await self.handle_error(e, "change_location_page", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "apply_location_markers", LocationStates.selecting_locations_for_marking)
        async def apply_location_markers(callback: CallbackQuery, state: FSMContext):
            """Apply location markers"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                data = await state.get_data()
                all_locations = data['all_locations']
                selected_locations = data['selected_locations']
                
                # Show processing message
                processing_msg = await callback.message.edit_text(t(bot_lang, 'locations.applying_markers'))
                
                updated_count = 0
                errors = []
                
                for location in all_locations:
                    try:
                        current_description = location.description or ''
                        has_marker = '[TGB]' in current_description
                        should_have_marker = str(location.id) in selected_locations
                        
                        # Only update if status changed
                        if has_marker != should_have_marker:
                            if should_have_marker:
                                new_description = f"{current_description} [TGB]".strip()
                            else:
                                new_description = current_description.replace('[TGB]', '').strip()
                            
                            success = await self.homebox_service.update_location(location.id, {
                                'description': new_description
                            })
                            
                            if success:
                                updated_count += 1
                            else:
                                errors.append(f"{location.name}: {self.homebox_service.last_error}")
                    
                    except Exception as e:
                        errors.append(f"{location.name}: {str(e)}")
                
                # Show result
                if updated_count > 0:
                    result_text = t(bot_lang, 'locations.markers_applied').format(count=updated_count)
                    if errors:
                        result_text += f"\n\n{t(bot_lang, 'locations.some_errors')}:\n" + "\n".join(errors[:5])
                else:
                    result_text = t(bot_lang, 'locations.no_changes')
                    if errors:
                        result_text += f"\n\n{t(bot_lang, 'locations.errors')}:\n" + "\n".join(errors[:5])
                
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await processing_msg.edit_text(
                    result_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                
            except Exception as e:
                await self.handle_error(e, "apply_location_markers", callback.from_user.id)
                await callback.answer(t('en', 'errors.occurred'))
        
        @self.router.callback_query(F.data == "cancel_location_marking", LocationStates.selecting_locations_for_marking)
        async def cancel_location_marking(callback: CallbackQuery, state: FSMContext):
            """Cancel location marking"""
            try:
                user_settings = await self.get_user_settings(callback.from_user.id)
                bot_lang = user_settings.bot_lang
                
                keyboard = self.keyboard_manager.location_management_keyboard(bot_lang)
                
                await callback.message.edit_text(
                    t(bot_lang, 'locations.marking_cancelled'),
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await state.clear()
                
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
    
    async def show_search_results(self, message: Message, state: FSMContext, items: list, page: int, lang: str, is_recent: bool = False):
        """Show search results with pagination"""
        try:
            # Ensure items is a list
            if not isinstance(items, list):
                logger.error(f"show_search_results: items is not a list, type={type(items)}, value={items}")
                items = []
            
            page_size = 5
            start_idx = page * page_size
            end_idx = start_idx + page_size
            page_items = items[start_idx:end_idx]
            
            if not page_items:
                try:
                    await message.edit_text(t(lang, 'search.no_results'))
                except:
                    await message.answer(t(lang, 'search.no_results'))
                return
            
            # Build results text
            title = t(lang, 'search.recent_title') if is_recent else t(lang, 'search.results_title')
            results_text = f"🔍 **{title}**\n\n"
            
            # Collect items with images for media group
            media_group = []
            
            for i, item in enumerate(page_items):
                # Ensure item is a dictionary
                if not isinstance(item, dict):
                    logger.error(f"show_search_results: item {i} is not a dict, type={type(item)}, value={item}")
                    continue
                    
                item_name = str(item.get('name', 'Unknown Item'))
                item_description = str(item.get('description', 'No description'))
                location = item.get('location', {})
                if isinstance(location, dict):
                    location_name = str(location.get('name', 'Unknown Location'))
                else:
                    location_name = 'Unknown Location'
                item_id = str(item.get('id', ''))
                image_id = item.get('imageId', '')
                
                # Truncate description if too long
                if len(item_description) > 100:
                    item_description = item_description[:97] + "..."
                
                results_text += f"**{start_idx + i + 1}.** {item_name}\n"
                results_text += f"📍 {location_name}\n"
                results_text += f"📝 {item_description}\n\n"
                
                # Add to media group if has image
                if image_id:
                    image_url = await self.homebox_service.get_image_url(image_id, item_id)
                    if image_url:
                        media_group.append(InputMediaPhoto(
                            media=image_url,
                            caption=f"**{start_idx + i + 1}.** {item_name}\n📍 {location_name}\n📝 {item_description}"
                        ))
            
            # Add pagination info
            total_pages = (len(items) + page_size - 1) // page_size
            results_text += f"📄 {t(lang, 'search.page_info')}: {page + 1}/{total_pages}"
            
            # Create keyboard
            keyboard = self.create_search_results_keyboard(page_items, page, total_pages, lang)
            
            # Try to send media group if we have images, otherwise send text
            logger.info(f"Media group size: {len(media_group)}")
            for i, media in enumerate(media_group):
                logger.info(f"Media {i}: {media.media}")
            
            if media_group and len(media_group) <= 10:  # Telegram limit is 10 media per group
                try:
                    await message.delete()
                    await message.answer_media_group(media_group)
                    # Send pagination info separately
                    await message.answer(
                        f"📄 {t(lang, 'search.page_info')}: {page + 1}/{total_pages}",
                        reply_markup=keyboard
                    )
                except Exception as media_error:
                    logger.warning(f"Failed to send media group: {media_error}")
                    # Fallback to text message
                    try:
                        await message.edit_text(
                            results_text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await message.answer(
                            results_text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
            else:
                # No images or too many, send text only
                try:
                    await message.edit_text(
                        results_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    await message.answer(
                        results_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
            
        except Exception as e:
            await self.handle_error(e, "show_search_results", message.from_user.id)
            try:
                await message.edit_text(t(lang, 'errors.occurred'))
            except:
                await message.answer(t(lang, 'errors.occurred'))
    
    def create_search_results_keyboard(self, items: list, current_page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
        """Create keyboard for search results"""
        keyboard = []
        
        # Ensure items is a list
        if not isinstance(items, list):
            logger.error(f"create_search_results_keyboard: items is not a list, type={type(items)}, value={items}")
            items = []
        
        # Add item buttons
        for i, item in enumerate(items):
            # Ensure item is a dictionary
            if not isinstance(item, dict):
                logger.error(f"create_search_results_keyboard: item {i} is not a dict, type={type(item)}, value={item}")
                continue
            item_name = str(item.get('name', 'Unknown Item'))
            item_id = str(item.get('id', ''))
            
            # Truncate name if too long
            if len(item_name) > 30:
                display_name = item_name[:30] + "..."
            else:
                display_name = item_name
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📦 {display_name}",
                    callback_data=f"search_item_{item_id}"
                )
            ])
        
        # Add pagination buttons
        if total_pages > 1:
            pagination_row = []
            
            if current_page > 0:
                pagination_row.append(
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data=f"search_page_{current_page - 1}"
                    )
                )
            
            pagination_row.append(
                InlineKeyboardButton(
                    text=f"{current_page + 1}/{total_pages}",
                    callback_data="noop"
                )
            )
            
            if current_page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data=f"search_page_{current_page + 1}"
                    )
                )
            
            keyboard.append(pagination_row)
        
        # Add control buttons
        keyboard.append([
            InlineKeyboardButton(
                text=t(lang, 'search.new_search'),
                callback_data="search_new"
            ),
            InlineKeyboardButton(
                text=t(lang, 'search.cancel'),
                callback_data="search_cancel"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def format_item_details(self, item: dict, lang: str) -> str:
        """Format item details for display"""
        name = str(item.get('name', 'Unknown Item'))
        description = str(item.get('description', 'No description'))
        location = item.get('location', {})
        if isinstance(location, dict):
            location_name = str(location.get('name', 'Unknown Location'))
        else:
            location_name = 'Unknown Location'
        quantity = item.get('quantity', 1)
        created_at = str(item.get('createdAt', ''))
        image_id = item.get('imageId', '')
        
        # Format creation date if available
        if created_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_str = dt.strftime('%d.%m.%Y %H:%M')
            except:
                created_str = created_at
        else:
            created_str = 'Unknown'
        
        details_text = f"""
📦 **{name}**

📍 **{t(lang, 'search.location')}**: {location_name}
📝 **{t(lang, 'search.description')}**: {description}
🔢 **{t(lang, 'search.quantity')}**: {quantity}
📅 **{t(lang, 'search.created')}**: {created_str}
        """.strip()
        
        return details_text
    
    async def get_item_image_url(self, item: dict) -> str:
        """Get image URL for item"""
        image_id = item.get('imageId', '')
        item_id = item.get('id', '')
        if image_id and item_id:
            return await self.homebox_service.get_image_url(image_id, item_id)
        return ""
