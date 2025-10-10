"""
Keyboard management for the bot
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from models.location import Location
from i18n.i18n_manager import t


class KeyboardManager:
    """Manages bot keyboards"""
    
    @staticmethod
    def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
        """Create main menu keyboard for quick navigation"""
        builder = InlineKeyboardBuilder()
        # First row
        builder.row(
            InlineKeyboardButton(text=f"🔍 {t(lang, 'menu.search')}", callback_data="open_search"),
            InlineKeyboardButton(text=f"📦 {t(lang, 'menu.recent')}", callback_data="open_recent")
        )
        # Second row
        builder.row(
            InlineKeyboardButton(text=f"⚙️ {t(lang, 'menu.settings')}", callback_data="open_settings"),
            InlineKeyboardButton(text=f"❓ {t(lang, 'menu.help')}", callback_data="open_help")
        )
        return builder.as_markup()

    @staticmethod
    def bot_lang_keyboard(current_lang: str) -> InlineKeyboardMarkup:
        """Create bot interface language selection keyboard"""
        builder = InlineKeyboardBuilder()
        ru_label = t(current_lang, 'languages.ru') + (" ✓" if current_lang == 'ru' else "")
        en_label = t(current_lang, 'languages.en') + (" ✓" if current_lang == 'en' else "")
        de_label = t(current_lang, 'languages.de') + (" ✓" if current_lang == 'de' else "")
        fr_label = t(current_lang, 'languages.fr') + (" ✓" if current_lang == 'fr' else "")
        es_label = t(current_lang, 'languages.es') + (" ✓" if current_lang == 'es' else "")
        builder.row(InlineKeyboardButton(text=ru_label, callback_data="bot_lang_ru"))
        builder.row(InlineKeyboardButton(text=en_label, callback_data="bot_lang_en"))
        builder.row(InlineKeyboardButton(text=de_label, callback_data="bot_lang_de"))
        builder.row(InlineKeyboardButton(text=fr_label, callback_data="bot_lang_fr"))
        builder.row(InlineKeyboardButton(text=es_label, callback_data="bot_lang_es"))
        
        # Back button
        builder.row(InlineKeyboardButton(text=t(current_lang, 'common.back'), callback_data="back_to_settings"))
        return builder.as_markup()
    
    @staticmethod
    def gen_lang_keyboard(bot_lang: str, current_gen_lang: str) -> InlineKeyboardMarkup:
        """Create generation language selection keyboard with UI in bot_lang and current selection marked"""
        builder = InlineKeyboardBuilder()
        ru_label = t(bot_lang, 'languages.ru') + (" ✓" if current_gen_lang == 'ru' else "")
        en_label = t(bot_lang, 'languages.en') + (" ✓" if current_gen_lang == 'en' else "")
        de_label = t(bot_lang, 'languages.de') + (" ✓" if current_gen_lang == 'de' else "")
        fr_label = t(bot_lang, 'languages.fr') + (" ✓" if current_gen_lang == 'fr' else "")
        es_label = t(bot_lang, 'languages.es') + (" ✓" if current_gen_lang == 'es' else "")
        builder.row(InlineKeyboardButton(text=ru_label, callback_data="gen_lang_ru"))
        builder.row(InlineKeyboardButton(text=en_label, callback_data="gen_lang_en"))
        builder.row(InlineKeyboardButton(text=de_label, callback_data="gen_lang_de"))
        builder.row(InlineKeyboardButton(text=fr_label, callback_data="gen_lang_fr"))
        builder.row(InlineKeyboardButton(text=es_label, callback_data="gen_lang_es"))
        
        # Back button
        builder.row(InlineKeyboardButton(text=t(bot_lang, 'common.back'), callback_data="back_to_settings"))
        return builder.as_markup()
    
    @staticmethod
    def settings_main_keyboard(bot_lang: str) -> InlineKeyboardMarkup:
        """Create main settings keyboard with improved layout"""
        builder = InlineKeyboardBuilder()

        # First row - languages (compact)
        builder.row(
            InlineKeyboardButton(text=f"🌐 {t(bot_lang, 'settings.bot_lang_title')}", callback_data="settings_bot_lang"),
            InlineKeyboardButton(text=f"📝 {t(bot_lang, 'settings.gen_lang_title')}", callback_data="settings_gen_lang")
        )

        # Second row - model and stats
        builder.row(
            InlineKeyboardButton(text=f"🧠 {t(bot_lang, 'settings.choose_model')}", callback_data="settings_model"),
            InlineKeyboardButton(text=f"📊 {t(bot_lang, 'settings.stats')}", callback_data="quick_stats")
        )

        # Third row - location management
        builder.row(
            InlineKeyboardButton(text=f"🏷️ {t(bot_lang, 'settings.location_management')}", callback_data="location_management")
        )

        # Fourth row - quick actions
        builder.row(
            InlineKeyboardButton(text=f"🔄 {t(bot_lang, 'settings.restart')}", callback_data="quick_restart")
        )

        return builder.as_markup()
    
    @staticmethod
    def confirmation_keyboard(bot_lang: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard with improved layout"""
        builder = InlineKeyboardBuilder()
        
        # First row - re-analyze (most important action)
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.reanalyze'), callback_data="reanalyze")
        )
        
        # Second row - edit actions (grouped)
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.edit_name'), callback_data="edit_name"),
            InlineKeyboardButton(text=t(bot_lang, 'buttons.edit_description'), callback_data="edit_description")
        )
        
        # Third row - location edit
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.edit_location'), callback_data="edit_location")
        )
        
        # Fourth row - main actions
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(bot_lang, 'buttons.confirm')}", callback_data="confirm"),
            InlineKeyboardButton(text=f"❌ {t(bot_lang, 'buttons.cancel')}", callback_data="cancel")
        )
        
        return builder.as_markup()

    @staticmethod
    def cancel_keyboard(bot_lang: str, callback: str = "cancel_edit") -> InlineKeyboardMarkup:
        """Create a simple keyboard with a single Cancel button"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=f"❌ {t(bot_lang, 'buttons.cancel')}", callback_data=callback))
        return builder.as_markup()

    @staticmethod
    def reanalysis_prompt_keyboard(bot_lang: str) -> InlineKeyboardMarkup:
        """Keyboard for reanalysis prompt: no-hint and cancel"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=f"🔄 {t(bot_lang, 'reanalysis.no_hint')}", callback_data="reanalyze_no_hint")
        )
        builder.row(
            InlineKeyboardButton(text=f"❌ {t(bot_lang, 'buttons.cancel')}", callback_data="cancel_reanalysis")
        )
        return builder.as_markup()
    
    @staticmethod
    def locations_keyboard(locations: List[Location], bot_lang: str) -> InlineKeyboardMarkup:
        """Create location selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        # Add each location on its own row
        for loc in locations:
            builder.row(
                InlineKeyboardButton(
                    text=loc.name,
                    callback_data=f"location_{loc.id}"
                )
            )
        
        # Back button only (no cancel during location edit)
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'common.back'), callback_data="back_to_confirm")
        )
        
        return builder.as_markup()
    
    @staticmethod
    def models_keyboard(current_model: str, available_models: List[str], lang: str = 'ru', page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
        """Create model selection keyboard with pagination"""
        builder = InlineKeyboardBuilder()
        
        start = page * page_size
        end = min(start + page_size, len(available_models))
        
        for model in available_models[start:end]:
            label = ("✓ " if model == current_model else "") + model
            builder.row(InlineKeyboardButton(text=label, callback_data=f"select_model_{model}"))
        
        # Navigation
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text=t(lang, 'common.previous'), callback_data=f"model_page_{page-1}"))
        if end < len(available_models):
            nav.append(InlineKeyboardButton(text=t(lang, 'common.next'), callback_data=f"model_page_{page+1}"))
        
        if nav:
            builder.row(*nav)
        
        # Back button
        builder.row(InlineKeyboardButton(text=t(lang, 'common.back'), callback_data="back_to_settings"))
        
        return builder.as_markup()
    
    def search_cancel_keyboard(self, lang: str) -> InlineKeyboardMarkup:
        """Create search cancel keyboard"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=t(lang, 'search.cancel'), callback_data="search_cancel"))
        return builder.as_markup()
    
    def item_details_keyboard(self, lang: str, item_id: str = None) -> InlineKeyboardMarkup:
        """Create item details keyboard"""
        builder = InlineKeyboardBuilder()
        
        # Edit buttons
        if item_id:
            builder.row(
                InlineKeyboardButton(text=t(lang, 'buttons.edit_name'), callback_data=f"edit_item_name_{item_id}"),
                InlineKeyboardButton(text=t(lang, 'buttons.edit_description'), callback_data=f"edit_item_desc_{item_id}")
            )
            builder.row(InlineKeyboardButton(text=t(lang, 'buttons.reanalyze'), callback_data=f"reanalyze_item_{item_id}"))
            builder.row(InlineKeyboardButton(text=f"📦 {t(lang, 'search.move_item')}", callback_data=f"move_item_{item_id}"))
            builder.row(InlineKeyboardButton(text=f"🗑️ {t(lang, 'search.delete_item')}", callback_data=f"delete_item_{item_id}"))
        
        # Navigation buttons
        builder.row(InlineKeyboardButton(text=t(lang, 'search.back_to_results'), callback_data="search_back"))
        builder.row(InlineKeyboardButton(text=t(lang, 'search.new_search'), callback_data="search_new"))
        return builder.as_markup()

    @staticmethod
    def delete_confirmation_keyboard(lang: str, item_id: str) -> InlineKeyboardMarkup:
        """Create delete confirmation keyboard for an item"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(lang, 'common.yes')}", callback_data=f"confirm_delete_{item_id}"),
            InlineKeyboardButton(text=f"❌ {t(lang, 'common.no')}", callback_data=f"cancel_delete_{item_id}")
        )
        builder.row(InlineKeyboardButton(text=t(lang, 'search.back_to_results'), callback_data="search_back"))
        return builder.as_markup()

    @staticmethod
    def reanalysis_confirmation_keyboard(lang: str, item_id: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard for applying reanalysis changes"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(lang, 'common.confirm')}", callback_data=f"confirm_reanalysis_{item_id}"),
            InlineKeyboardButton(text=f"❌ {t(lang, 'common.cancel')}", callback_data=f"reject_reanalysis_{item_id}")
        )
        return builder.as_markup()
    
    @staticmethod
    def move_item_location_keyboard(locations: List[Location], current_location_id: str, lang: str, item_id: str) -> InlineKeyboardMarkup:
        """Create location selection keyboard for moving items"""
        builder = InlineKeyboardBuilder()
        
        # Add each location on its own row
        for i, loc in enumerate(locations):
            # Skip current location
            if str(loc.id) == str(current_location_id):
                continue
            
            # Use short callback data with index instead of full UUID
            # Format: mov_loc_<index> - we'll store mapping in state
            builder.row(
                InlineKeyboardButton(
                    text=f"📍 {loc.name}",
                    callback_data=f"mov_loc_{i}"
                )
            )
        
        # Back button with short callback data
        builder.row(
            InlineKeyboardButton(text=t(lang, 'common.back'), callback_data="mov_back")
        )
        
        return builder.as_markup()
    
    @staticmethod
    def location_management_keyboard(lang: str) -> InlineKeyboardMarkup:
        """Create location management keyboard"""
        builder = InlineKeyboardBuilder()
        
        # New: Create location at the very top
        builder.row(
            InlineKeyboardButton(text=f"🆕 {t(lang, 'locations.create_location')}", callback_data="create_location")
        )
        
        builder.row(
            InlineKeyboardButton(text=f"🏷️ {t(lang, 'locations.mark_locations')}", callback_data="mark_locations")
        )
        builder.row(
            InlineKeyboardButton(text=f"🤖 {t(lang, 'locations.generate_descriptions')}", callback_data="generate_location_descriptions")
        )
        builder.row(
            InlineKeyboardButton(text=f"📋 {t(lang, 'locations.view_all')}", callback_data="view_all_locations")
        )
        builder.row(
            InlineKeyboardButton(text=t(lang, 'common.back'), callback_data="back_to_settings")
        )
        
        return builder.as_markup()

    @staticmethod
    def parent_locations_keyboard(locations: List[Location], lang: str, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
        """Create parent location selection keyboard with pagination. Includes 'no parent' option."""
        builder = InlineKeyboardBuilder()
        
        # Special option: no parent
        builder.row(
            InlineKeyboardButton(text=t(lang, 'locations.no_parent'), callback_data="parent_none")
        )
        
        start = page * page_size
        end = min(start + page_size, len(locations))
        for loc in locations[start:end]:
            builder.row(
                InlineKeyboardButton(text=f"📍 {loc.name}", callback_data=f"parent_{loc.id}")
            )
        
        # Navigation
        total_pages = (len(locations) + page_size - 1) // page_size
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text=t(lang, 'common.previous'), callback_data=f"parent_page_{page-1}"))
        if end < len(locations):
            nav.append(InlineKeyboardButton(text=t(lang, 'common.next'), callback_data=f"parent_page_{page+1}"))
        if nav:
            builder.row(*nav)
        
        # Cancel/back
        builder.row(InlineKeyboardButton(text=t(lang, 'common.back'), callback_data="cancel_create_location"))
        
        return builder.as_markup()
    
    @staticmethod
    def locations_selection_keyboard(locations: List[Location], lang: str, page: int = 0, page_size: int = 10, selected_locations: set = None) -> InlineKeyboardMarkup:
        """Create location selection keyboard for marking"""
        builder = InlineKeyboardBuilder()
        
        start = page * page_size
        end = min(start + page_size, len(locations))
        
        if selected_locations is None:
            selected_locations = set()
            
        for loc in locations[start:end]:
            # Show marker status based on current selection
            is_selected = str(loc.id) in selected_locations
            marker_icon = "✅" if is_selected else "⬜"
            display_name = f"{marker_icon} {loc.name}"
            
            builder.row(
                InlineKeyboardButton(
                    text=display_name,
                    callback_data=f"toggle_location_{loc.id}"
                )
            )
        
        # Navigation
        total_pages = (len(locations) + page_size - 1) // page_size
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text=t(lang, 'common.previous'), callback_data=f"location_page_{page-1}"))
            if end < len(locations):
                nav.append(InlineKeyboardButton(text=t(lang, 'common.next'), callback_data=f"location_page_{page+1}"))
            
            if nav:
                builder.row(*nav)
        
        # Action buttons
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(lang, 'locations.apply_markers')}", callback_data="apply_location_markers"),
            InlineKeyboardButton(text=f"❌ {t(lang, 'locations.cancel')}", callback_data="cancel_location_marking")
        )
        
        return builder.as_markup()
    
    @staticmethod
    def location_description_selection_keyboard(locations: List[Location], lang: str, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
        """Create location selection keyboard for description generation (only [TGB] marked locations)"""
        builder = InlineKeyboardBuilder()
        
        # Filter only locations with [TGB] marker
        marked_locations = [loc for loc in locations if '[TGB]' in (loc.description or '')]
        
        start = page * page_size
        end = min(start + page_size, len(marked_locations))
        
        for loc in marked_locations[start:end]:
            display_name = f"📍 {loc.name}"
            
            builder.row(
                InlineKeyboardButton(
                    text=display_name,
                    callback_data=f"generate_desc_{loc.id}"
                )
            )
        
        # Navigation
        total_pages = (len(marked_locations) + page_size - 1) // page_size
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text=t(lang, 'common.previous'), callback_data=f"desc_page_{page-1}"))
            if end < len(marked_locations):
                nav.append(InlineKeyboardButton(text=t(lang, 'common.next'), callback_data=f"desc_page_{page+1}"))
            
            if nav:
                builder.row(*nav)
        
        # Action buttons
        builder.row(
            InlineKeyboardButton(text=f"❌ {t(lang, 'locations.cancel')}", callback_data="cancel_description_generation")
        )
        
        return builder.as_markup()
    
    @staticmethod
    def restart_confirmation_keyboard(lang: str) -> InlineKeyboardMarkup:
        """Create restart confirmation keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(lang, 'restart.confirm_yes')}", callback_data="confirm_restart"),
            InlineKeyboardButton(text=f"❌ {t(lang, 'restart.confirm_no')}", callback_data="cancel_restart")
        )
        
        return builder.as_markup()
    
    @staticmethod
    def description_confirmation_keyboard(lang: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard for description update"""
        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(lang, 'common.yes')}", callback_data="confirm_description_update"),
            InlineKeyboardButton(text=f"❌ {t(lang, 'common.no')}", callback_data="reject_description_update")
        )
        builder.row(
            InlineKeyboardButton(text=f"🔄 {t(lang, 'common.regenerate')}", callback_data="regenerate_description")
        )
        
        return builder.as_markup()

    @staticmethod
    def create_desc_confirmation_keyboard(lang: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard for create-location AI description preview"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=f"✅ {t(lang, 'common.confirm')}", callback_data="create_desc_confirm"),
            InlineKeyboardButton(text=f"❌ {t(lang, 'locations.cancel')}", callback_data="create_desc_cancel")
        )
        builder.row(
            InlineKeyboardButton(text=f"🔄 {t(lang, 'common.regenerate')}", callback_data="create_desc_regen"),
            InlineKeyboardButton(text=f"🧠 {t(lang, 'locations.generate_with_ai')}", callback_data="create_desc_regen_with_hint")
        )
        return builder.as_markup()