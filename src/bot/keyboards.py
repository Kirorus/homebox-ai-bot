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
    def gen_lang_keyboard(current_lang: str) -> InlineKeyboardMarkup:
        """Create generation language selection keyboard"""
        builder = InlineKeyboardBuilder()
        ru_label = t(current_lang, 'languages.ru') + (" ✓" if current_lang == 'ru' else "")
        en_label = t(current_lang, 'languages.en') + (" ✓" if current_lang == 'en' else "")
        de_label = t(current_lang, 'languages.de') + (" ✓" if current_lang == 'de' else "")
        fr_label = t(current_lang, 'languages.fr') + (" ✓" if current_lang == 'fr' else "")
        es_label = t(current_lang, 'languages.es') + (" ✓" if current_lang == 'es' else "")
        builder.row(InlineKeyboardButton(text=ru_label, callback_data="gen_lang_ru"))
        builder.row(InlineKeyboardButton(text=en_label, callback_data="gen_lang_en"))
        builder.row(InlineKeyboardButton(text=de_label, callback_data="gen_lang_de"))
        builder.row(InlineKeyboardButton(text=fr_label, callback_data="gen_lang_fr"))
        builder.row(InlineKeyboardButton(text=es_label, callback_data="gen_lang_es"))
        
        # Back button
        builder.row(InlineKeyboardButton(text=t(current_lang, 'common.back'), callback_data="back_to_settings"))
        return builder.as_markup()
    
    @staticmethod
    def settings_main_keyboard(bot_lang: str) -> InlineKeyboardMarkup:
        """Create main settings keyboard"""
        builder = InlineKeyboardBuilder()

        # First row - languages
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'settings.bot_lang_title'), callback_data="settings_bot_lang"),
            InlineKeyboardButton(text=t(bot_lang, 'settings.gen_lang_title'), callback_data="settings_gen_lang")
        )

        # Second row - model
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'settings.choose_model'), callback_data="settings_model")
        )

        # Third row - quick actions
        builder.row(
            InlineKeyboardButton(text=f"📊 {t(bot_lang, 'settings.stats')}", callback_data="quick_stats"),
            InlineKeyboardButton(text=f"🔄 {t(bot_lang, 'settings.restart')}", callback_data="quick_restart")
        )

        return builder.as_markup()
    
    @staticmethod
    def confirmation_keyboard(bot_lang: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard"""
        builder = InlineKeyboardBuilder()
        
        # First row - edit name
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.edit_name'), callback_data="edit_name")
        )
        
        # Second row - edit description
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.edit_description'), callback_data="edit_description")
        )
        
        # Third row - edit location
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.edit_location'), callback_data="edit_location")
        )
        
        # Fourth row - re-analyze
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.reanalyze'), callback_data="reanalyze")
        )
        
        # Fifth row - confirm action
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.confirm'), callback_data="confirm")
        )
        
        # Sixth row - cancel action
        builder.row(
            InlineKeyboardButton(text=t(bot_lang, 'buttons.cancel'), callback_data="cancel")
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
        
        # Back button
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
            builder.row(InlineKeyboardButton(text=label, callback_data=f"model_{model}"))
        
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
