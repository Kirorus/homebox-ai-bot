"""
Search handling logic
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from .base_handler import BaseHandler
from bot.states import SearchStates
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
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang),
                            parse_mode="Markdown"
                        )
                    except Exception as photo_error:
                        logger.warning(f"Failed to send photo for item {item_id}: {photo_error}")
                        # Fallback to text message
                        await callback.message.answer(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang),
                            parse_mode="Markdown"
                        )
                else:
                    # No image, send text only
                    try:
                        await callback.message.edit_text(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang),
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        await callback.message.answer(
                            details_text,
                            reply_markup=self.keyboard_manager.item_details_keyboard(bot_lang),
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
